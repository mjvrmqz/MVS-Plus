"""
YouTube Channel Scanner
========================
Reads search titles from GitHub repo mjvrmqz/MVS-Studios,
searches YouTube for each, scans result videos for title similarity,
checks matching channels for social links, and logs everything to Notion.
Automatically rotates through multiple API keys when quota is hit.

Setup:
    /opt/homebrew/bin/python3.13 -m pip install google-api-python-client rapidfuzz requests --break-system-packages

Usage:
    Set API_KEYS and NOTION_KEY in the CONFIG section, then:
    /opt/homebrew/bin/python3.13 "YouTube Scraper.py"
"""

import os
import re
import time
import json
import base64
import random
import requests
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from rapidfuzz import fuzz

# ─────────────────────────────────────────────
#  CONFIG — reads from environment variables
#  (set as GitHub Actions secrets, or export
#   them in your shell for local runs)
# ─────────────────────────────────────────────
API_KEYS = [k for k in [
    os.environ.get("YT_API_KEY_1"),
    os.environ.get("YT_API_KEY_2"),
    os.environ.get("YT_API_KEY_3"),
] if k]

NOTION_KEY   = os.environ.get("NOTION_KEY", "")
SOURCE_DB_ID = os.environ.get("SOURCE_DB_ID", "")

GITHUB_TITLES_URL = (
    "https://raw.githubusercontent.com/mjvrmqz/MVS-Studios/main/"
    "Outreach/Scrapers/YouTube/Search%20Titles.txt"
)

GITHUB_TOKEN   = os.environ.get("GH_PAT", "")
GITHUB_API_URL = "https://api.github.com/repos/mjvrmqz/MVS-Studios/contents/Outreach/Scrapers/YouTube/Search%20Titles.txt"

OUTPUT_FILE            = "scan_results.json"
SIMILARITY_THRESHOLD   = 60
MAX_CONSECUTIVE_MISSES = 15
RESULTS_PER_PAGE       = 10
MAX_PAGES              = 5
REQUEST_DELAY          = 0.5
MIN_VIDEO_SECONDS      = 300   # 5 minutes
MAX_VIDEO_AGE_DAYS     = 730   # 2 years — skip anything older
MIN_SUBSCRIBERS        = 10_000  # ignore channels below this

# ─────────────────────────────────────────────
#  KEY ROTATION
# ─────────────────────────────────────────────

_key_index = 0
_youtube   = None


def get_youtube():
    global _youtube, _key_index
    if _youtube is None:
        _youtube = build("youtube", "v3", developerKey=API_KEYS[_key_index])
        log(f"Using API key [{_key_index + 1}/{len(API_KEYS)}]")
    return _youtube


def rotate_key() -> bool:
    global _youtube, _key_index
    _key_index += 1
    if _key_index >= len(API_KEYS):
        log("❌ All API keys exhausted for today. Stopping.")
        return False
    _youtube = build("youtube", "v3", developerKey=API_KEYS[_key_index])
    log(f"🔑 Rotated to API key [{_key_index + 1}/{len(API_KEYS)}]")
    return True


def is_quota_error(e: HttpError) -> bool:
    return e.resp.status == 429 or any(
        x in str(e) for x in ("quotaExceeded", "rateLimitExceeded")
    )


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def github_headers() -> dict:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def load_titles_from_github() -> tuple:
    """
    Returns (pending_titles_shuffled, all_lines, file_sha).
    Lines already ending in ' ✓' are skipped.
    """
    log("Fetching titles from GitHub...")
    resp = requests.get(GITHUB_TITLES_URL, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch titles from GitHub: {resp.status_code}")

    all_lines = resp.text.splitlines()

    sha = None
    if GITHUB_TOKEN:
        meta = requests.get(GITHUB_API_URL, headers=github_headers(), timeout=10)
        if meta.status_code == 200:
            sha = meta.json().get("sha")

    pending = [l.strip() for l in all_lines if l.strip() and not l.strip().endswith(" ✓")]
    random.shuffle(pending)

    done_count = sum(1 for l in all_lines if l.strip().endswith(" ✓"))
    log(f"Loaded {len(pending)} pending titles ({done_count} already done) — randomised")
    return pending, all_lines, sha


def mark_title_done(title: str, all_lines: list, sha: str) -> list:
    """Appends ' ✓' to the matching line and pushes the file back to GitHub."""
    if not GITHUB_TOKEN:
        log("  ⚠ No GitHub token set — skipping mark-as-done")
        return all_lines, sha

    updated = []
    for line in all_lines:
        if line.strip() == title and not line.strip().endswith(" ✓"):
            updated.append(line.rstrip() + " ✓")
        else:
            updated.append(line)

    new_content = "\n".join(updated) + "\n"
    encoded     = base64.b64encode(new_content.encode()).decode()

    payload = {
        "message": f"✓ Mark done: {title[:60]}",
        "content": encoded,
        "sha":     sha,
    }

    resp = requests.put(GITHUB_API_URL, headers=github_headers(), json=payload, timeout=15)
    if resp.status_code in (200, 201):
        log(f"  ✓ GitHub: marked done → \"{title[:60]}\"")
        new_sha = resp.json().get("content", {}).get("sha") or resp.json().get("commit", {}).get("sha")
        return updated, new_sha
    else:
        log(f"  ⚠ GitHub write failed [{resp.status_code}]: {resp.text[:200]}")
        return updated, sha


def is_similar(video_title: str, search_query: str):
    score = max(
        fuzz.token_set_ratio(video_title.lower(), search_query.lower()),
        fuzz.partial_ratio(video_title.lower(), search_query.lower())
    )
    return score >= SIMILARITY_THRESHOLD, score


def extract_social_links(text: str) -> dict:
    patterns = {
        "Twitter":   r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[A-Za-z0-9_]+',
        "Instagram": r'https?://(?:www\.)?instagram\.com/[A-Za-z0-9_.]+',
        "TikTok":    r'https?://(?:www\.)?tiktok\.com/@[A-Za-z0-9_.]+',
        "Facebook":  r'https?://(?:www\.)?facebook\.com/[A-Za-z0-9_.]+',
        "LinkedIn":  r'https?://(?:www\.)?linkedin\.com/(?:in|company)/[A-Za-z0-9_-]+',
    }
    found = {}
    for platform, pattern in patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            found[platform] = matches[0]
    return found


# ─────────────────────────────────────────────
#  NOTION — DB SCHEMA PROBE
# ─────────────────────────────────────────────

def notion_probe_db():
    url  = f"https://api.notion.com/v1/databases/{SOURCE_DB_ID}"
    resp = requests.get(url, headers=notion_headers())
    data = resp.json()
    props = data.get("properties", {})
    log("── Notion DB properties ──")
    for name, info in props.items():
        log(f"  '{name}' → {info.get('type')}")
    log("─────────────────────────")
    return props


_notion_headers_cache = None


def notion_headers() -> dict:
    global _notion_headers_cache
    if _notion_headers_cache is None:
        _notion_headers_cache = {
            "Authorization": f"Bearer {NOTION_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
    return _notion_headers_cache


def notion_get_existing() -> tuple:
    existing_urls     = set()
    existing_channels = set()
    url     = f"https://api.notion.com/v1/databases/{SOURCE_DB_ID}/query"
    payload = {"page_size": 100}
    while True:
        resp = requests.post(url, headers=notion_headers(), json=payload)
        data = resp.json()
        for page in data.get("results", []):
            props      = page.get("properties", {})
            post_url   = (props.get("Post") or {}).get("url", "")
            select_val = ((props.get("Select") or {}).get("select") or {}).get("name", "")
            channel_id_list = (props.get("ChannelID") or {}).get("rich_text", [])
            channel_id = channel_id_list[0].get("text", {}).get("content", "") if channel_id_list else ""

            if select_val == "Leads" and post_url:
                existing_urls.add(post_url)
            if select_val == "Leads" and channel_id:
                existing_channels.add(channel_id)

        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]

    log(f"Notion: loaded {len(existing_urls)} Lead URLs, {len(existing_channels)} known channels")
    return existing_urls, existing_channels


def proxy(url: str) -> str:
    """Wrap a URL in wsrv.nl so Notion accepts YouTube CDN image URLs."""
    return f"https://wsrv.nl/?url={requests.utils.quote(url, safe='')}"


def notion_add_entry(video_id: str, video_title: str, channel_id: str, channel_name: str,
                     is_match: bool, social_links: dict,
                     profile_pic: str = None, banner: str = None):
    video_url    = f"https://www.youtube.com/watch?v={video_id}"
    select_value = "Leads" if is_match else "Scraped"

    properties = {
        "Post":      {"url": video_url},
        "Select":    {"select": {"name": select_value}},
        "Name":      {"title": [{"text": {"content": channel_name}}]},
        "ChannelID": {"rich_text": [{"text": {"content": channel_id}}]},
    }

    social_order    = ["Twitter", "Instagram", "TikTok", "Facebook", "LinkedIn"]
    social_assigned = False
    for platform in social_order:
        if platform in social_links:
            if not social_assigned:
                properties["Social"] = {"url": social_links[platform]}
                social_assigned = True
            else:
                properties[platform] = {"url": social_links[platform]}

    if not social_assigned:
        properties["Social"] = {"url": None}

    payload = {
        "parent":     {"database_id": SOURCE_DB_ID},
        "properties": properties,
    }

    if profile_pic:
        payload["icon"] = {"type": "external", "external": {"url": proxy(profile_pic)}}

    if banner:
        safe_banner = f"https://wsrv.nl/?url={requests.utils.quote(banner, safe='')}&blur=8&brightness=40"
        payload["cover"] = {"type": "external", "external": {"url": safe_banner}}

    if profile_pic:
        payload["children"] = [
            {
                "object": "block",
                "type":   "image",
                "image":  {
                    "type":     "external",
                    "external": {"url": proxy(profile_pic)},
                    "caption":  []
                }
            }
        ]

    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=notion_headers(),
        json=payload
    )

    if resp.status_code not in (200, 201):
        log(f"  ⚠ Notion insert failed [{resp.status_code}]: {resp.text[:400]}")
    else:
        result_select = resp.json().get("properties", {}).get("Select", {}).get("select", {}).get("name", "?")
        log(f"  ✓ Notion: logged '{video_title[:50]}' as {select_value} (Notion confirmed: {result_select})")


# ─────────────────────────────────────────────
#  YOUTUBE API
# ─────────────────────────────────────────────

def search_videos(query: str, page_token: str = None) -> dict:
    params = {
        "q":             query,
        "part":          "snippet",
        "type":          "video",
        "videoDuration": "medium",
        "maxResults":    RESULTS_PER_PAGE,
        "fields":        "nextPageToken,items(id/videoId,snippet/title,snippet/channelId,snippet/channelTitle,snippet/publishedAt)"
    }
    if page_token:
        params["pageToken"] = page_token
    return get_youtube().search().list(**params).execute()


def get_video_duration_seconds(video_id: str) -> int:
    try:
        resp = get_youtube().videos().list(
            id=video_id,
            part="contentDetails",
            fields="items(contentDetails/duration)"
        ).execute()
        if not resp.get("items"):
            return 0
        raw   = resp["items"][0]["contentDetails"]["duration"]
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', raw)
        if not match:
            return 0
        h = int(match.group(1) or 0)
        m = int(match.group(2) or 0)
        s = int(match.group(3) or 0)
        return h * 3600 + m * 60 + s
    except HttpError:
        return 0


def get_channel_about(channel_id: str) -> dict:
    response = get_youtube().channels().list(
        id=channel_id,
        part="snippet,brandingSettings",
        fields="items(snippet/description,brandingSettings/channel/keywords)"
    ).execute()
    if not response.get("items"):
        return {"description": "", "social_links": {}}
    item        = response["items"][0]
    description = item.get("snippet", {}).get("description", "")
    keywords    = item.get("brandingSettings", {}).get("channel", {}).get("keywords", "")
    full_text   = description + " " + keywords
    return {
        "description":  description[:300] + "..." if len(description) > 300 else description,
        "social_links": extract_social_links(full_text)
    }


def get_channel_images(channel_id: str) -> dict:
    try:
        resp = get_youtube().channels().list(
            id=channel_id,
            part="snippet,brandingSettings,statistics",
            fields="items(snippet/thumbnails,brandingSettings/image/bannerExternalUrl,statistics/subscriberCount)"
        ).execute()
        if not resp.get("items"):
            return {"profile_pic": None, "banner": None, "subscribers": 0}
        item        = resp["items"][0]
        thumbs      = item.get("snippet", {}).get("thumbnails", {})
        profile_pic = (
            thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}
        ).get("url")
        banner      = item.get("brandingSettings", {}).get("image", {}).get("bannerExternalUrl")
        subscribers = int(item.get("statistics", {}).get("subscriberCount", 0))
        log(f"    📷 profile_pic={profile_pic}")
        log(f"    🎨 banner={banner}")
        log(f"    👥 subscribers={subscribers:,}")
        return {"profile_pic": profile_pic, "banner": banner, "subscribers": subscribers}
    except HttpError:
        return {"profile_pic": None, "banner": None, "subscribers": 0}


# ─────────────────────────────────────────────
#  CORE SCANNER
# ─────────────────────────────────────────────

def scan_title(search_query: str, already_scanned: set, already_seen_channels: set) -> list:
    log(f"\n{'─'*60}")
    log(f"SCANNING: \"{search_query}\"")
    log(f"{'─'*60}")

    matches            = []
    consecutive_misses = 0
    page_token         = None
    page_num           = 0
    total_scanned      = 0

    while page_num < MAX_PAGES:
        try:
            time.sleep(REQUEST_DELAY)
            response = search_videos(search_query, page_token)
        except HttpError as e:
            if is_quota_error(e):
                log(f"  ⚠ Quota hit on key [{_key_index + 1}], rotating...")
                if rotate_key():
                    continue
                else:
                    return matches
            log(f"  ⚠ API error on search: {e}")
            break

        items = response.get("items", [])
        if not items:
            log("  No more results from API.")
            break

        for item in items:
            video_id     = item["id"]["videoId"]
            video_title  = item["snippet"]["title"]
            channel_id   = item["snippet"]["channelId"]
            channel_name = item["snippet"]["channelTitle"]
            total_scanned += 1

            video_url = f"https://www.youtube.com/watch?v={video_id}"

            if video_url in already_scanned:
                log(f"  ~ skip (already in Notion) | \"{video_title[:60]}\"")
                continue

            time.sleep(REQUEST_DELAY)
            try:
                duration = get_video_duration_seconds(video_id)
            except HttpError as e:
                if is_quota_error(e):
                    if not rotate_key():
                        return matches
                    duration = get_video_duration_seconds(video_id)
                else:
                    duration = 0

            if duration < MIN_VIDEO_SECONDS:
                log(f"  ~ skip (too short: {duration}s) | \"{video_title[:60]}\"")
                continue

            published_at = item["snippet"].get("publishedAt", "")
            if published_at:
                pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - pub_date).days
                if age_days > MAX_VIDEO_AGE_DAYS:
                    log(f"  ~ skip (too old: {age_days}d) | \"{video_title[:60]}\"")
                    continue

            matched, score = is_similar(video_title, search_query)

            try:
                time.sleep(REQUEST_DELAY)
                images = get_channel_images(channel_id)
            except HttpError as e:
                if is_quota_error(e):
                    if not rotate_key():
                        return matches
                    images = get_channel_images(channel_id)
                else:
                    log(f"    ⚠ Could not fetch channel images: {e}")
                    images = {"profile_pic": None, "banner": None, "subscribers": 0}

            if channel_id in already_seen_channels:
                log(f"  ~ skip (channel already a Lead) | {channel_name}")
                continue

            if images.get("subscribers", 0) < MIN_SUBSCRIBERS:
                log(f"  ~ skip (too small: {images.get('subscribers', 0):,} subs) | {channel_name}")
                continue

            if matched:
                log(f"  ✓ MATCH (score={score}) | \"{video_title}\" — {channel_name}")

                try:
                    time.sleep(REQUEST_DELAY)
                    about = get_channel_about(channel_id)
                except HttpError as e:
                    if is_quota_error(e):
                        if not rotate_key():
                            return matches
                        about = get_channel_about(channel_id)
                    else:
                        log(f"    ⚠ Could not fetch channel info: {e}")
                        about = {"description": "", "social_links": {}}

                social = about["social_links"]
                if social:
                    log(f"    🔗 Socials: {', '.join(f'{p}: {u}' for p, u in social.items())}")
                else:
                    log(f"    — No social links found")

                notion_add_entry(
                    video_id, video_title, channel_id, channel_name,
                    is_match=True, social_links=social,
                    profile_pic=images["profile_pic"],
                    banner=images["banner"]
                )
                already_scanned.add(video_url)
                already_seen_channels.add(channel_id)

                matches.append({
                    "search_query": search_query,
                    "video_id":     video_id,
                    "video_title":  video_title,
                    "channel_id":   channel_id,
                    "channel_name": channel_name,
                    "similarity":   score,
                    "social_links": social,
                })

                consecutive_misses = 0

            else:
                consecutive_misses += 1
                log(f"  · skip (score={score:>3}) | \"{video_title[:60]}\"")

                notion_add_entry(
                    video_id, video_title, channel_id, channel_name,
                    is_match=False, social_links={},
                    profile_pic=images["profile_pic"],
                    banner=images["banner"]
                )
                already_scanned.add(video_url)
                # NOTE: do NOT add to already_seen_channels for Scraped entries

                if consecutive_misses >= MAX_CONSECUTIVE_MISSES:
                    log(f"  ↩ {MAX_CONSECUTIVE_MISSES} consecutive misses — moving on.")
                    return matches

        page_token = response.get("nextPageToken")
        if not page_token:
            log("  Reached last page of results.")
            break

        page_num += 1

    log(f"  Done. Scanned {total_scanned} videos, found {len(matches)} matches.")
    return matches


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    if not API_KEYS:
        print("❌ No YouTube API keys found. Set YT_API_KEY_1/2/3 environment variables.")
        return
    if not NOTION_KEY:
        print("❌ No Notion key found. Set NOTION_KEY environment variable.")
        return
    if not GITHUB_TOKEN:
        log("⚠ No GitHub PAT found (GH_PAT env var) — titles will NOT be marked as done.")

    notion_probe_db()

    titles, all_lines, sha  = load_titles_from_github()
    already_scanned, already_seen_channels = notion_get_existing()
    all_results             = []

    for i, title in enumerate(titles, 1):
        log(f"\n[{i}/{len(titles)}] Queue: \"{title}\"")
        matches = scan_title(title, already_scanned, already_seen_channels)
        all_results.extend(matches)

        all_lines, sha = mark_title_done(title, all_lines, sha)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        if _key_index >= len(API_KEYS):
            log("All keys exhausted, ending run.")
            break

    log(f"\n{'═'*60}")
    log(f"SCAN COMPLETE")
    log(f"  Titles searched : {len(titles)}")
    log(f"  Total matches   : {len(all_results)}")
    log(f"  With socials    : {sum(1 for r in all_results if r['social_links'])}")
    log(f"{'═'*60}")


if __name__ == "__main__":
    main()
