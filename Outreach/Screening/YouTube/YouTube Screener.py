"""
YouTube Screener.py

Reads "Leads" from the YouTube Scraper Notion database, scores each channel
for outreach compatibility, then creates NEW entries in the Screening database.

The source (scraper) database is NEVER modified — leads remain exactly as-is.
"""

# ─── SCORING CONSTANTS ────────────────────────────────────────────────────────

WEIGHT_UPLOAD_FREQ  = 0.40   # 40%
WEIGHT_TITLE_STYLE  = 0.40   # 40%
WEIGHT_SOCIAL       = 0.20   # 20%

FREQ_IDEAL_MIN      = 3.0    # ideal uploads/week lower bound
FREQ_IDEAL_MAX      = 4.0    # ideal uploads/week upper bound
FREQ_TOO_HIGH       = 5.0    # above this → heavy penalty
FREQ_TOO_LOW        = 0.25   # below this (≈1/month) → heavy penalty

VIDEO_SAMPLE_SIZE   = 50     # how many recent videos to analyse
MIN_SUBSCRIBERS     = 10_000
X_FOLLOWER_SAMPLE   = 300    # how many X followers to sample (name-only check)

X_COOKIES_URL = "https://raw.githubusercontent.com/mjvrmqz/MVS-Studios/refs/heads/main/Outreach/Scrapers/X/x_cookies.json"

# ─── IMPORTS ──────────────────────────────────────────────────────────────────

import asyncio
import os
import re
import time
import logging
from datetime import datetime

import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ─── ENVIRONMENT / CREDENTIALS ────────────────────────────────────────────────

NOTION_KEY    = os.environ["NOTION_KEY"]

# YouTube API keys with automatic fallback
YT_API_KEYS = [
    os.environ["YT_API_KEY_1"],
    os.environ["YT_API_KEY_2"],
    os.environ["YT_API_KEY_3"],
]

SOURCE_DB_ID   = os.environ["SOURCE_DB_ID"]   # Scraper DB (read-only)
OUTREACH_DB_ID = os.environ["OUTREACH_DB_ID"]  # Outreach DB (write)

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
    """
    Wraps the YouTube API and automatically falls back to the next API key
    if the current one hits a quota error (403 or 429).
    """
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
    """
    Gets the uploads playlist ID for a channel.
    Uses channels().list (1 quota unit) instead of search().list (100 units).
    """
    resp = yt.execute(
        lambda c: c.channels().list(part="contentDetails", id=channel_id)
    )
    items = resp.get("items", [])
    if not items:
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

def get_recent_videos(yt, channel_id, max_results=VIDEO_SAMPLE_SIZE):
    """
    Fetches recent videos via playlistItems (1 unit/call) instead of
    search.list (100 units/call) to preserve daily quota.
    Normalises output to the same shape as search.list so downstream
    scoring logic (uploads_per_week, title_style_score) is unchanged.
    """
    playlist_id = get_uploads_playlist_id(yt, channel_id)
    if not playlist_id:
        return []

    videos, page_token = [], None
    while len(videos) < max_results:
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
        if not page_token:
            break
    return videos

def get_video_title(yt, video_id):
    if not video_id:
        return ""
    resp  = yt.execute(lambda c: c.videos().list(part="snippet", id=video_id))
    items = resp.get("items", [])
    return items[0]["snippet"]["title"] if items else ""

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

# ─── TITLE STYLE SCORE (0–100) ────────────────────────────────────────────────

def _title_features(title):
    t     = title.strip()
    words = t.split()
    first = words[0].lower() if words else ""
    caps  = sum(1 for w in words if w.isupper() and len(w) > 1)
    tc    = sum(1 for w in words if w and w[0].isupper())
    return {
        "len_short":      int(len(words) <= 4),
        "len_medium":     int(5 <= len(words) <= 8),
        "len_long":       int(len(words) > 8),
        "has_caps":       int(caps > 0),
        "has_ellipsis":   int("…" in t or "..." in t),
        "is_question":    int("?" in t),
        "starts_how_why": int(first in ("how", "why", "when", "what", "where")),
        "personal_i":     int(t.startswith("I ") or t.startswith("I'")),
        "title_case":     int(tc / max(len(words), 1) > 0.6),
        "has_emoji":      int(bool(re.search(r"[\U00010000-\U0010ffff]", t))),
        "clickbait":      int(bool(re.search(
            r"(insane|crazy|unbelievable|shocking|gone wrong|epic|exposed)", t, re.I))),
        "narrative":      int(bool(re.search(
            r"\b(became|fell|lost|found|died|rose|built|destroyed|saved|changed|ruined)\b",
            t, re.I))),
    }

def _feature_similarity(f1, f2):
    keys = set(f1) | set(f2)
    matches = sum(1 for k in keys if f1.get(k, 0) == f2.get(k, 0))
    return matches / len(keys) if keys else 0

def title_style_score(lead_title, channel_titles):
    if not lead_title or not channel_titles:
        return 50
    lead_feats = _title_features(lead_title)
    chan_feats  = [_title_features(t) for t in channel_titles if t]
    if not chan_feats:
        return 50
    avg_sim = sum(_feature_similarity(lead_feats, cf) for cf in chan_feats) / len(chan_feats)
    if avg_sim >= 0.65:
        score = 70 + (avg_sim - 0.65) / 0.35 * 30
    elif avg_sim >= 0.45:
        score = 40 + (avg_sim - 0.45) / 0.20 * 30
    else:
        score = avg_sim / 0.45 * 40
    return round(min(100, max(0, score)))

# ─── X / TWITTER SCRAPING ─────────────────────────────────────────────────────

# Keywords checked against display name only (no profile page visits)
EDITOR_NAME_KEYWORDS = [
    "editor",
    "video editor",
    "vfx",
]

def _name_has_editor_signals(display_name):
    name_lower = display_name.lower()
    return any(kw in name_lower for kw in EDITOR_NAME_KEYWORDS)

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
    names    = [c["name"] for c in cookies]
    has_auth = "auth_token" in names
    has_ct0  = "ct0" in names
    log.info(f"Loaded {len(cookies)} cookies — auth_token: {'YES' if has_auth else 'MISSING'}, ct0: {'YES' if has_ct0 else 'MISSING'}")
    return cookies

async def _collect_followers_with_names(page, username, max_followers):
    """
    Scrolls the followers page and collects (username, display_name) pairs.
    No individual profile pages are visited — names come from the follower list cells.
    """
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

    followers    = []   # list of (username, display_name)
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
    """
    Collects up to sample_size followers and checks their display names only
    for editor-related keywords. No profile page visits.
    """
    cookies = load_x_cookies()
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
        "parent": {"database_id": OUTREACH_DB_ID},
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

    log.info("Fetching Leads from Notion scraper database (read-only)...")
    all_pages = query_database(SOURCE_DB_ID)
    leads     = [p for p in all_pages if select_val(p, "Select") == "Leads"]
    log.info(f"Found {len(leads)} Lead(s) to process")

    for page in leads:
        channel_id = text_val(page, "ChannelID")
        post_url   = url_val(page, "Post")
        page_id    = page["id"]

        if not channel_id:
            log.warning(f"Page {page_id}: no ChannelID, skipping")
            continue

        log.info(f"Processing channel: {channel_id}")

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

        upw     = uploads_per_week(videos)
        f_score = upload_frequency_score(upw)
        log.info(f"  Upload freq: {upw:.2f}/wk → score {f_score}")

        video_id   = video_id_from_url(post_url)
        lead_title = ""
        if video_id:
            try:
                lead_title = get_video_title(yt, video_id)
            except Exception:
                pass
        t_score = title_style_score(lead_title, channel_titles)
        log.info(f"  Title style: {t_score}  (lead title: '{lead_title}')")

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

    log.info("YouTube Screener complete.")

def video_id_from_url(url):
    for pat in [r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", r"shorts/([A-Za-z0-9_-]{11})"]:
        m = re.search(pat, url or "")
        if m:
            return m.group(1)
    return None

if __name__ == "__main__":
    main()
