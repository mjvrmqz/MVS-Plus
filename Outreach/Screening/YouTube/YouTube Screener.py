"""
YouTube Screener.py

Reads "Leads" from the YouTube Scraper Notion database, scores each channel
for outreach compatibility, then creates NEW entries in the Screening database.

After a successful screening entry is created, the lead's Select property
is updated to "Finished" so it is skipped on the next run.

Title style scoring uses Phi-3 Mini (local, free) to evaluate tone and format
against the reference titles in Search Titles.txt. The model is explicitly
unloaded from memory before Playwright launches to avoid RAM pressure.
"""

# ─── SCORING CONSTANTS ────────────────────────────────────────────────────────

WEIGHT_UPLOAD_FREQ  = 0.40
WEIGHT_TITLE_STYLE  = 0.40
WEIGHT_SOCIAL       = 0.20

FREQ_IDEAL_MIN      = 3.0
FREQ_IDEAL_MAX      = 4.0
FREQ_TOO_HIGH       = 5.0
FREQ_TOO_LOW        = 0.25

VIDEO_SAMPLE_SIZE   = 50
MIN_SUBSCRIBERS     = 10_000
X_FOLLOWER_SAMPLE   = 300

X_COOKIES_URL     = "https://raw.githubusercontent.com/mjvrmqz/MVS-Studios/refs/heads/main/Outreach/Scrapers/X/x_cookies.json"
SEARCH_TITLES_URL = "https://raw.githubusercontent.com/mjvrmqz/MVS-Studios/refs/heads/main/Outreach/Scrapers/YouTube/Search%20Titles.txt"

PHI3_MODEL = "microsoft/Phi-3-mini-4k-instruct"

# ─── IMPORTS ──────────────────────────────────────────────────────────────────

import asyncio
import gc
import os
import re
import time
import logging
from datetime import datetime

import requests
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ─── ENVIRONMENT / CREDENTIALS ────────────────────────────────────────────────

NOTION_KEY = os.environ["NOTION_KEY"]

YT_API_KEYS = [
    os.environ["YT_API_KEY_1"],
    os.environ["YT_API_KEY_2"],
    os.environ["YT_API_KEY_3"],
]

SOURCE_DB_ID    = os.environ["SOURCE_DB_ID"]
SCREENING_DB_ID = os.environ["SCREENING_DB_ID"]

NOTION_VERSION = "2022-06-28"
NOTION_BASE    = "https://api.notion.com/v1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── YOUTUBE CLIENT WITH KEY ROTATION ─────────────────────────────────────────

class YouTubeClient:
    def __init__(self, keys):
        self.keys      = keys
        self.key_index = 0
        self.client    = self._build()

    def _build(self):
        key = self.keys[self.key_index]
        log.info(f"Using YouTube API key #{self.key_index + 1}")
        return build("youtube", "v3", developerKey=key)

    def _rotate(self):
        self.key_index += 1
        if self.key_index >= len(self.keys):
            raise RuntimeError("All YouTube API keys have been exhausted.")
        log.warning(f"Quota hit — rotating to API key #{self.key_index + 1}")
        self.client = self._build()

    def execute(self, request_fn):
        while True:
            try:
                return request_fn(self.client).execute()
            except HttpError as e:
                if e.resp.status in (403, 429):
                    self._rotate()
                else:
                    raise

# ─── NOTION HELPERS ───────────────────────────────────────────────────────────

def notion_headers():
    return {
        "Authorization":  f"Bearer {NOTION_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type":   "application/json",
    }

def notion_post(path, body):
    resp = requests.post(f"{NOTION_BASE}{path}", headers=notion_headers(), json=body)
    resp.raise_for_status()
    return resp.json()

def notion_patch(path, body):
    resp = requests.patch(f"{NOTION_BASE}{path}", headers=notion_headers(), json=body)
    resp.raise_for_status()
    return resp.json()

def query_database(db_id, filter_body=None):
    pages, payload = [], {}
    if filter_body:
        payload["filter"] = filter_body
    has_more, cursor = True, None
    while has_more:
        if cursor:
            payload["start_cursor"] = cursor
        data     = notion_post(f"/databases/{db_id}/query", payload)
        pages   += data.get("results", [])
        has_more = data.get("has_more", False)
        cursor   = data.get("next_cursor")
    return pages

def mark_lead_finished(page_id):
    notion_patch(f"/pages/{page_id}", {
        "properties": {
            "Select": {"select": {"name": "Finished"}}
        }
    })

# ─── PROPERTY EXTRACTORS ──────────────────────────────────────────────────────

def prop(page, key):
    return page.get("properties", {}).get(key)

def text_val(page, key):
    p = prop(page, key)
    if not p:
        return ""
    t = p.get("type", "")
    if t == "rich_text":
        return "".join(x["plain_text"] for x in p.get("rich_text", []))
    if t == "title":
        return "".join(x["plain_text"] for x in p.get("title", []))
    return ""

def url_val(page, key):
    p = prop(page, key)
    return (p or {}).get("url") or ""

def select_val(page, key):
    p = prop(page, key)
    if not p:
        return ""
    sel = p.get("select")
    return sel.get("name", "") if sel else ""

def all_urls_on_page(page):
    urls = []
    for key, p in page.get("properties", {}).items():
        if not p:
            continue
        t = p.get("type", "")
        if t == "url" and p.get("url"):
            urls.append(p["url"])
        elif t == "rich_text":
            for block in p.get("rich_text", []):
                href = block.get("href") or block.get("plain_text", "")
                if href and href.startswith("http"):
                    urls.append(href)
    return urls

# ─── IMAGE PROXY ──────────────────────────────────────────────────────────────

def wsrv(url, w=None, h=None, blur=None, brightness=None):
    if not url:
        return url
    params = f"url={requests.utils.quote(url, safe='')}"
    if w:          params += f"&w={w}"
    if h:          params += f"&h={h}"
    if blur:       params += f"&blur={blur}"
    if brightness: params += f"&mod={brightness}"
    return f"https://wsrv.nl/?{params}"

# ─── YOUTUBE API CALLS ────────────────────────────────────────────────────────

def get_channel_info(yt, channel_id):
    resp  = yt.execute(
        lambda c: c.channels().list(part="snippet,statistics,brandingSettings", id=channel_id)
    )
    items = resp.get("items", [])
    return items[0] if items else None

def get_uploads_playlist_id(yt, channel_id):
    resp = yt.execute(
        lambda c: c.channels().list(part="contentDetails", id=channel_id)
    )
    items = resp.get("items", [])
    if not items:
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

def get_recent_videos(yt, channel_id, max_results=VIDEO_SAMPLE_SIZE):
    playlist_id = get_uploads_playlist_id(yt, channel_id)
    if not playlist_id:
        return []

    videos, page_token = [], None
    while True:
        batch = min(50, max_results - len(videos))
        def make_request(c, pt=page_token, b=batch, pl=playlist_id):
            kwargs = dict(part="snippet", playlistId=pl, maxResults=b)
            if pt:
                kwargs["pageToken"] = pt
            return c.playlistItems().list(**kwargs)
        resp = yt.execute(make_request)
        for item in resp.get("items", []):
            sn = item.get("snippet", {})
            videos.append({
                "snippet": {
                    "title":       sn.get("title", ""),
                    "publishedAt": sn.get("publishedAt", ""),
                    "resourceId":  sn.get("resourceId", {}),
                }
            })
        page_token = resp.get("nextPageToken")
        if len(videos) >= max_results or not page_token:
            break
    return videos

# ─── UPLOAD FREQUENCY SCORE (0–100) ───────────────────────────────────────────

def uploads_per_week(videos):
    if len(videos) < 2:
        return 0.0
    dates = []
    for v in videos:
        pub = v["snippet"].get("publishedAt", "")
        if pub:
            dates.append(datetime.fromisoformat(pub.replace("Z", "+00:00")))
    if len(dates) < 2:
        return 0.0
    dates.sort(reverse=True)
    span_weeks = (dates[0] - dates[-1]).total_seconds() / (86400 * 7)
    return len(dates) / span_weeks if span_weeks > 0 else 0.0

def upload_frequency_score(upw):
    if upw <= 0:
        return 0
    if FREQ_IDEAL_MIN <= upw <= FREQ_IDEAL_MAX:
        return 100
    if upw > FREQ_TOO_HIGH:
        return max(0, round(100 - (upw - FREQ_TOO_HIGH) * 20))
    if upw < FREQ_TOO_LOW:
        return round((upw / FREQ_TOO_LOW) * 30)
    if upw > FREQ_IDEAL_MAX:
        ratio = (FREQ_TOO_HIGH - upw) / (FREQ_TOO_HIGH - FREQ_IDEAL_MAX)
        return round(50 + ratio * 50)
    ratio = (upw - FREQ_TOO_LOW) / (FREQ_IDEAL_MIN - FREQ_TOO_LOW)
    return round(30 + ratio * 70)

# ─── SEARCH TITLES LOADER ─────────────────────────────────────────────────────

def load_search_titles():
    log.info("Fetching Search Titles.txt from GitHub...")
    resp = requests.get(SEARCH_TITLES_URL, timeout=10)
    resp.raise_for_status()
    titles = [line.strip() for line in resp.text.splitlines() if line.strip()]
    log.info(f"Loaded {len(titles)} reference titles")
    return titles

# ─── PHI-3 MINI TITLE SCORING ─────────────────────────────────────────────────

def load_phi3():
    """
    Loads Phi-3 Mini tokenizer and model directly.
    Avoids the pipeline() API which has compatibility issues in transformers 5.x.
    """
    log.info("Loading Phi-3 Mini model...")
    tokenizer = AutoTokenizer.from_pretrained(PHI3_MODEL, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        PHI3_MODEL,
        dtype=torch.float32,         # CPU-safe
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    model.eval()
    log.info("Phi-3 Mini loaded.")
    return model, tokenizer

def unload_phi3(model, tokenizer):
    """Explicitly removes Phi-3 from memory before Playwright launches."""
    log.info("Unloading Phi-3 Mini to free RAM...")
    del model, tokenizer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    log.info("Phi-3 Mini unloaded.")

def title_style_score(model, tokenizer, channel_titles, reference_titles):
    """
    Uses Phi-3 Mini to score how well a channel's titles match the tone and
    format of the reference titles in Search Titles.txt.

    Returns (score: int, reason: str).
    """
    if not channel_titles:
        return 50, "No channel titles available — title score neutral"
    if not reference_titles:
        return 50, "No reference titles loaded — title score neutral"

    prompt = (
        f"<|user|>\n"
        f"You are evaluating whether a YouTube channel is a good fit for a video editing agency "
        f"that works with documentary and commentary-style creators.\n\n"
        f"The agency is specifically looking for channels with this underlying tone and format:\n"
        f"- Narrative or investigative framing (e.g. \"The Downfall of X\", \"How X Destroyed Their Career\")\n"
        f"- Subject-driven, story-arc structure — there is a clear subject and something happens to them\n"
        f"- Serious, analytical, or dramatic energy — NOT vlog, prank, challenge, or hype content\n"
        f"- Titles feel like documentary episode titles or long-form essay titles\n\n"
        f"Reference titles representing the IDEAL tone and format:\n"
        + "\n".join(f"- {t}" for t in reference_titles)
        + f"\n\nChannel's recent video titles:\n"
        + "\n".join(f"- {t}" for t in channel_titles)
        + f"\n\nScore 0-100 where:\n"
        f"90-100: Almost every title fits the documentary/commentary tone perfectly\n"
        f"70-89: Majority fit, occasional off-tone video\n"
        f"50-69: Mixed — some commentary but also unrelated content\n"
        f"30-49: Mostly doesn't fit, maybe a few commentary titles\n"
        f"0-29: Wrong tone entirely — vlog, prank, gaming, lifestyle, hype\n\n"
        f"Respond with exactly two lines, nothing else:\n"
        f"SCORE: <integer 0-100>\n"
        f"REASON: <one sentence>\n"
        f"<|end|>\n<|assistant|>\n"
    )

    try:
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=3072)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=60,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        # Decode only the newly generated tokens (not the prompt)
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response   = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        log.debug(f"  Phi-3 raw response: {response!r}")

        score  = 50
        reason = "Could not parse model response"

        for line in response.splitlines():
            line = line.strip()
            if line.upper().startswith("SCORE:"):
                m = re.search(r"\d+", line)
                if m:
                    score = max(0, min(100, int(m.group())))
            elif line.upper().startswith("REASON:"):
                reason = line.split(":", 1)[-1].strip()

        return score, reason

    except Exception as e:
        log.warning(f"  Phi-3 title scoring failed ({e}) — defaulting to 50")
        return 50, "Model scoring unavailable — title score neutral"

# ─── X / TWITTER SCRAPING ─────────────────────────────────────────────────────

EDITOR_NAME_KEYWORDS = ["editor", "video editor", "vfx"]

def _name_has_editor_signals(display_name):
    return any(kw in display_name.lower() for kw in EDITOR_NAME_KEYWORDS)

def _extract_x_username(url):
    m = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)", url or "")
    return m.group(1) if m else None

def load_x_cookies():
    log.info("Fetching X cookies from GitHub...")
    resp = requests.get(X_COOKIES_URL, timeout=10)
    resp.raise_for_status()
    raw = resp.json()
    cookies = []
    for c in raw:
        cookie = {
            "name":     c.get("name", ""),
            "value":    c.get("value", ""),
            "domain":   c.get("domain", ".x.com"),
            "path":     c.get("path", "/"),
            "secure":   c.get("secure", False),
            "httpOnly": c.get("httpOnly", False),
        }
        if cookie["name"] and cookie["value"]:
            cookies.append(cookie)
    names = [c["name"] for c in cookies]
    log.info(f"Loaded {len(cookies)} cookies — auth_token: {'YES' if 'auth_token' in names else 'MISSING'}, ct0: {'YES' if 'ct0' in names else 'MISSING'}")
    return cookies

async def _collect_followers_with_names(page, username, max_followers):
    url = f"https://x.com/{username}/followers"
    log.info(f"  Opening followers page: {url}")
    await page.goto(url, wait_until="domcontentloaded")
    await asyncio.sleep(3)

    if "login" in page.url or "i/flow" in page.url:
        log.error("Redirected to login — X cookies may be expired.")
        return []

    try:
        await page.wait_for_selector('[data-testid="UserCell"]', timeout=15000)
    except PlaywrightTimeout:
        log.warning(f"  Follower cells never loaded for @{username}.")
        return []

    followers    = []
    seen         = set()
    last_count   = 0
    stale_rounds = 0
    skip_names   = {"home", "explore", "notifications", "messages", "search",
                    "settings", "i", "login", "logout", "signup", username.lower()}

    while len(followers) < max_followers and stale_rounds < 4:
        cells = await page.query_selector_all('[data-testid="UserCell"]')
        for cell in cells:
            link = await cell.query_selector('a[href^="/"]')
            if not link:
                continue
            href  = await link.get_attribute("href")
            if not href:
                continue
            uname = href.strip("/").split("/")[0]
            if not uname or uname in skip_names or uname in seen:
                continue
            display_name = ""
            name_el = await cell.query_selector('[data-testid="UserName"] span')
            if name_el:
                display_name = (await name_el.inner_text()).strip()
            seen.add(uname)
            followers.append((uname, display_name))

        if len(followers) == last_count:
            stale_rounds += 1
        else:
            stale_rounds = 0
            last_count   = len(followers)
            log.info(f"  Collected {len(followers)} followers so far...")

        if len(followers) < max_followers:
            await page.evaluate("window.scrollBy(0, 1500)")
            await asyncio.sleep(1.5)

    log.info(f"  Final follower count: {len(followers)}")
    return followers[:max_followers]

async def scrape_x_editor_signals(x_username, sample_size=X_FOLLOWER_SAMPLE):
    cookies      = load_x_cookies()
    editor_count = 0
    total_count  = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        for cookie in cookies:
            try:
                await context.add_cookies([cookie])
            except Exception:
                pass

        page = await context.new_page()
        await page.goto("https://x.com/home", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        logged_in = await page.query_selector('[data-testid="SideNav_AccountSwitcher_Button"]')
        if not logged_in:
            log.error("X cookies didn't authenticate — please update x_cookies.json in GitHub.")
            await browser.close()
            return 0, 0

        log.info("  X session authenticated.")
        followers = await _collect_followers_with_names(page, x_username, sample_size)
        if not followers:
            await browser.close()
            return 0, 0

        log.info(f"  Checking display names for editor signals ({len(followers)} followers)...")
        for uname, display_name in followers:
            total_count += 1
            if _name_has_editor_signals(display_name):
                editor_count += 1
                log.info(f"    Editor signal: @{uname} ({display_name!r})")

        await browser.close()

    return editor_count, total_count

def social_score(page):
    all_urls   = all_urls_on_page(page)
    x_url      = next((u for u in all_urls if "twitter.com" in u or "x.com" in u), None)

    if not x_url:
        return 50, "No X/Twitter profile found — social score neutral"

    x_username = _extract_x_username(x_url)
    if not x_username:
        return 50, "Could not parse X username — social score neutral"

    log.info(f"  Scraping X followers for @{x_username}")
    editor_count, total_count = asyncio.run(
        scrape_x_editor_signals(x_username, sample_size=X_FOLLOWER_SAMPLE)
    )

    if total_count == 0:
        return 50, "No follower data collected — social score neutral"

    ratio = editor_count / total_count
    note  = f"{editor_count}/{total_count} sampled followers have editor signals in name ({ratio:.1%})"

    if ratio >= 0.05:
        score = min(100, round(60 + ratio * 400))
    elif ratio >= 0.01:
        score = round(40 + ratio * 2000)
    elif ratio > 0:
        score = 30
    else:
        score = 20

    return score, note

# ─── COMPATIBILITY RATE ────────────────────────────────────────────────────────

def compatibility_rate(freq_score, title_score, soc_score):
    return round(
        freq_score  * WEIGHT_UPLOAD_FREQ +
        title_score * WEIGHT_TITLE_STYLE +
        soc_score   * WEIGHT_SOCIAL
    )

# ─── SCREENING ENTRY CREATION ─────────────────────────────────────────────────

def create_screening_entry(channel_info, channel_id, compat_rate):
    snippet  = channel_info["snippet"]
    stats    = channel_info.get("statistics", {})
    branding = channel_info.get("brandingSettings", {})

    name       = snippet.get("title", "Unknown")
    subs       = stats.get("subscriberCount", "0")
    thumb_url  = (
        snippet.get("thumbnails", {}).get("high", {}).get("url") or
        snippet.get("thumbnails", {}).get("default", {}).get("url") or ""
    )
    banner_url = branding.get("image", {}).get("bannerExternalUrl", "")

    icon_url  = wsrv(thumb_url, w=200, h=200)
    cover_url = wsrv(banner_url, blur=5, brightness=70) if banner_url else None
    embed_url = wsrv(thumb_url, w=400)

    body = {
        "parent": {"database_id": SCREENING_DB_ID},
        "icon":   {"type": "external", "external": {"url": icon_url}},
        "properties": {
            "Name":               {"title":     [{"text": {"content": name}}]},
            "Subscribers":        {"rich_text": [{"text": {"content": subs}}]},
            "Platform Link":      {"url": f"https://www.youtube.com/channel/{channel_id}"},
            "Compatibility Rate": {"number": compat_rate},
            "Source":             {"select": {"name": "YouTube"}},
        },
        "children": [
            {
                "object": "block",
                "type":   "image",
                "image":  {"type": "external", "external": {"url": embed_url}},
            }
        ],
    }

    if cover_url:
        body["cover"] = {"type": "external", "external": {"url": cover_url}}

    return notion_post("/pages", body)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    log.info("Starting YouTube Screener")
    yt = YouTubeClient(YT_API_KEYS)

    try:
        reference_titles = load_search_titles()
    except Exception as e:
        log.error(f"Failed to load Search Titles.txt: {e} — title scoring will be neutral")
        reference_titles = []

    # Load Phi-3 once — unloaded before Playwright runs
    phi3_model = phi3_tokenizer = None
    if reference_titles:
        try:
            phi3_model, phi3_tokenizer = load_phi3()
        except Exception as e:
            log.error(f"Failed to load Phi-3: {e} — title scoring will be neutral")

    log.info("Fetching Leads from Notion scraper database...")
    all_pages = query_database(SOURCE_DB_ID)
    leads     = [p for p in all_pages if select_val(p, "Select") == "Leads"]
    log.info(f"Found {len(leads)} Lead(s) to process")

    # ── Phase 1: Score all channels while Phi-3 is in memory ──────────────────
    scored_leads = []

    for page in leads:
        channel_id = text_val(page, "ChannelID")
        page_id    = page["id"]

        if not channel_id:
            log.warning(f"Page {page_id}: no ChannelID, skipping")
            continue

        log.info(f"Scoring channel: {channel_id}")

        try:
            ch_info = get_channel_info(yt, channel_id)
        except Exception as e:
            log.error(f"  YouTube error: {e}")
            continue

        if not ch_info:
            log.warning("  Channel not found on YouTube, skipping")
            continue

        subs = int(ch_info.get("statistics", {}).get("subscriberCount", 0))
        if subs < MIN_SUBSCRIBERS:
            log.info(f"  Only {subs} subscribers — skipping")
            continue

        try:
            videos = get_recent_videos(yt, channel_id)
        except Exception as e:
            log.error(f"  Could not fetch videos: {e}")
            videos = []

        channel_titles = [
            v["snippet"]["title"] for v in videos
            if v.get("snippet", {}).get("title")
        ]
        log.info(f"  Got {len(channel_titles)} titles to score")

        upw     = uploads_per_week(videos)
        f_score = upload_frequency_score(upw)
        log.info(f"  Upload freq: {upw:.2f}/wk → score {f_score}")

        if phi3_model and reference_titles:
            t_score, t_reason = title_style_score(phi3_model, phi3_tokenizer, channel_titles, reference_titles)
        else:
            t_score, t_reason = 50, "Phi-3 unavailable — title score neutral"
        log.info(f"  Title style: {t_score}  ({t_reason})")

        scored_leads.append((page, ch_info, channel_id, f_score, t_score, t_reason, videos))

    # ── Unload Phi-3 before launching Playwright ───────────────────────────────
    if phi3_model is not None:
        unload_phi3(phi3_model, phi3_tokenizer)
        phi3_model = phi3_tokenizer = None

    # ── Phase 2: Social scoring + entry creation ───────────────────────────────
    for page, ch_info, channel_id, f_score, t_score, t_reason, videos in scored_leads:
        page_id = page["id"]

        s_score, s_note = social_score(page)
        log.info(f"  Social score: {s_score}  ({s_note})")

        compat = compatibility_rate(f_score, t_score, s_score)
        log.info(f"  → Compatibility Rate: {compat}%")

        try:
            result = create_screening_entry(ch_info, channel_id, compat)
            log.info(f"  Screening entry created: {result.get('url', result.get('id'))}")
        except Exception as e:
            log.error(f"  Failed to create screening entry: {e}")
            time.sleep(0.5)
            continue

        try:
            mark_lead_finished(page_id)
            log.info(f"  Marked lead {page_id} as Finished")
        except Exception as e:
            log.error(f"  Failed to mark lead as Finished: {e}")

        time.sleep(0.5)

    log.info("YouTube Screener complete.")

if __name__ == "__main__":
    main()
