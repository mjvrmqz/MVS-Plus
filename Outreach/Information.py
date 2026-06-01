#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
#  Information.py  ·  MVS Studios / Outreach
#  Paste a URL (YouTube, X, Discord, Skool) → push to Notion
#  YouTube links also pull channel stats into the page body.
# ─────────────────────────────────────────────────────────────

import subprocess, json, sys, os, re, requests, statistics
from datetime import datetime

# ── Config ────────────────────────────────────────────────────
NOTION_TOKEN  = "ntn_U60582391564u7rDIIxeSyYXMD7aOqEaawu30A8D3wUag7"
DATABASE_ID   = "28d1691964b48065b59ec1f0b293f91f"
YTDLP         = "/Library/Frameworks/Python.framework/Versions/3.13/bin/yt-dlp"
SAMPLE_VIDEOS = 15   # videos used for engagement / frequency stats

# ── Source Detection ──────────────────────────────────────────

def detect_source(url):
    """Return the platform name matching the URL, or None if unrecognised."""
    url_lower = url.lower()
    if re.search(r'(youtube\.com|youtu\.be)', url_lower):
        return "YouTube"
    if re.search(r'(twitter\.com|x\.com)', url_lower):
        return "X"
    if re.search(r'discord\.com|discord\.gg', url_lower):
        return "Discord"
    if re.search(r'skool\.com', url_lower):
        return "Skool"
    return None

# ── Helpers ───────────────────────────────────────────────────

def fmt_num(n):
    if n is None: return "N/A"
    if n >= 1_000_000: return f"{n/1_000_000:.2f}M"
    if n >= 1_000:     return f"{n/1_000:.1f}K"
    return str(n)

def fmt_duration(secs):
    if not secs: return "N/A"
    secs = int(secs)
    h, rem = divmod(secs, 3600)
    m, s   = divmod(rem,   60)
    if h:   return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"

def run(args, label=""):
    if label: print(f"  {label}", end="", flush=True)
    r = subprocess.run([YTDLP] + args, capture_output=True, text=True)
    if label: print(" ✓")
    if r.returncode != 0 and r.stderr:
        print(f"\n  [yt-dlp warn] {r.stderr.strip()[:200]}")
    return r.stdout.strip()

# ── Resolve URL ───────────────────────────────────────────────

def resolve_channel_url(raw_url):
    """If given a video URL, extract the channel URL from it."""
    if re.search(r'(watch\?v=|youtu\.be/)', raw_url):
        print("  Resolving channel from video URL...")
        out = run(["--dump-json", "--no-playlist", raw_url])
        if out:
            try:
                info = json.loads(out.splitlines()[0])
                ch = info.get("channel_url") or info.get("uploader_url")
                if ch:
                    print(f"  Channel URL → {ch}")
                    return ch
            except Exception:
                pass
    return raw_url

# ── Fetch data ────────────────────────────────────────────────

def get_channel_meta(url):
    """Channel-level metadata + flat entry list (fast)."""
    out = run(
        ["--dump-single-json", "--flat-playlist",
         "--playlist-items", f"1-{SAMPLE_VIDEOS * 2}",
         url],
        "Fetching channel metadata..."
    )
    if not out: return None
    return json.loads(out)

def get_video_details(url):
    """Full per-video JSON (views, likes, comments, duration, date)."""
    out = run(
        ["--dump-json",
         "--playlist-items", f"1-{SAMPLE_VIDEOS}",
         "--no-warnings",
         url],
        f"Fetching stats from last {SAMPLE_VIDEOS} videos..."
    )
    videos = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try: videos.append(json.loads(line))
            except Exception: pass
    return videos

# ── Stats ─────────────────────────────────────────────────────

def upload_frequency(videos):
    """Returns uploads/week based on date spread."""
    dates = []
    for v in videos:
        d = v.get("upload_date")
        if d:
            try: dates.append(datetime.strptime(d, "%Y%m%d"))
            except ValueError: pass
    if len(dates) < 2: return None
    dates.sort(reverse=True)
    span_days = (dates[0] - dates[-1]).days
    if span_days == 0: return None
    return round(len(dates) / (span_days / 7), 2)

def extract_thumbnails(channel_data):
    """Return (avatar_url, banner_url) from yt-dlp channel JSON."""
    thumbs = channel_data.get("thumbnails", [])
    avatar = banner = None

    for t in thumbs:
        tid = str(t.get("id", "")).lower()
        url = t.get("url", "")
        if not url: continue
        if "avatar" in tid or "avatar" in url.lower():
            if not avatar or (t.get("width", 0) or 0) > 100:
                avatar = url
        elif "banner" in tid or "banner" in url.lower():
            if not banner or (t.get("width", 0) or 0) > 500:
                banner = url

    if not avatar and thumbs:
        avatar = thumbs[-1].get("url")
    if not banner and len(thumbs) > 1:
        candidates = sorted(thumbs, key=lambda t: t.get("width", 0) or 0, reverse=True)
        for c in candidates:
            if c.get("url") != avatar:
                banner = c.get("url")
                break

    return avatar, banner

def compute_stats(meta, videos):
    name = (
        meta.get("channel")
        or meta.get("uploader")
        or meta.get("title", "Unknown")
    )
    subscribers  = meta.get("channel_follower_count")
    channel_url  = (
        meta.get("channel_url")
        or meta.get("uploader_url")
        or meta.get("webpage_url")
    )
    avatar_url, banner_url = extract_thumbnails(meta)

    frequency    = upload_frequency(videos)
    durations    = [v.get("duration") for v in videos if v.get("duration")]
    avg_duration = statistics.mean(durations) if durations else None

    view_counts  = [v.get("view_count") for v in videos if v.get("view_count")]
    avg_views    = statistics.mean(view_counts) if view_counts else None
    vr = round((avg_views / subscribers * 100), 4) if avg_views and subscribers else None

    eng_totals = []
    for v in videos:
        l = v.get("like_count") or 0
        c = v.get("comment_count") or 0
        if l or c: eng_totals.append(l + c)
    avg_eng = statistics.mean(eng_totals) if eng_totals else None
    er = round((avg_eng / subscribers * 100), 4) if avg_eng and subscribers else None

    avg_views_raw = int(avg_views) if avg_views else None
    avg_likes     = int(statistics.mean([v.get("like_count") or 0 for v in videos])) if videos else None
    avg_comments  = int(statistics.mean([v.get("comment_count") or 0 for v in videos if v.get("comment_count") is not None])) if videos else None
    total_vids    = meta.get("playlist_count") or len(meta.get("entries", []))

    return dict(
        name         = name,
        subscribers  = subscribers,
        frequency    = frequency,
        avg_duration = avg_duration,
        avg_views    = avg_views_raw,
        avg_likes    = avg_likes,
        avg_comments = avg_comments,
        vr           = vr,
        er           = er,
        total_videos = total_vids,
        channel_url  = channel_url,
        avatar_url   = avatar_url,
        banner_url   = banner_url,
    )

# ── Notion helpers ────────────────────────────────────────────

def get_db_schema():
    """Retrieve actual property names + types from the database."""
    r = requests.get(
        f"https://api.notion.com/v1/databases/{DATABASE_ID}",
        headers={
            "Authorization":  f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
        }
    )
    if r.status_code == 200:
        return r.json().get("properties", {})
    print(f"  [warn] Could not fetch DB schema: {r.status_code} — {r.text[:200]}")
    return {}

def build_property(prop_type, value):
    """Return a Notion property value dict based on property type."""
    if value is None: return None
    if isinstance(value, str) and prop_type == "number": prop_type = "rich_text"
    if prop_type == "title":
        return {"title": [{"text": {"content": str(value)}}]}
    if prop_type == "rich_text":
        return {"rich_text": [{"text": {"content": str(value)}}]}
    if prop_type == "number":
        return {"number": value}
    if prop_type == "url":
        return {"url": str(value)}
    if prop_type == "select":
        return {"select": {"name": str(value)}}
    if prop_type == "multi_select":
        return {"multi_select": [{"name": str(value)}]}
    return {"rich_text": [{"text": {"content": str(value)}}]}

def resolve_prop_name(schema, col_name):
    """Case-insensitive lookup of a column name in the schema."""
    return next((k for k in schema if k.lower() == col_name.lower()), col_name)

# ── Notion page creation ──────────────────────────────────────

def build_stats_table_blocks(stats):
    """
    Return a list of Notion block dicts that form a simple table
    showing YouTube channel statistics inside the page body.
    Notion tables need at least 2 columns; we use Stat | Value.
    """
    rows = [
        ("Stat",             "Value"),   # header row
        ("Channel",          stats["name"]),
        ("Subscribers",      fmt_num(stats["subscribers"])),
        ("Total Videos",     str(stats["total_videos"]) if stats["total_videos"] else "N/A"),
        ("Upload Frequency", (str(stats["frequency"]) + " videos/week") if stats["frequency"] else "N/A"),
        ("Avg Video Length", fmt_duration(stats["avg_duration"])),
        ("Avg Views",        fmt_num(stats["avg_views"])),
        ("Avg Likes",        fmt_num(stats["avg_likes"])),
        ("Avg Comments",     fmt_num(stats["avg_comments"])),
        ("View Ratio (VR%)", (str(stats["vr"]) + "%") if stats["vr"] else "N/A"),
        ("Engagement Rate",  (str(stats["er"]) + "%") if stats["er"] else "N/A"),
        ("Channel URL",      stats["channel_url"] or "N/A"),
    ]

    table_rows = []
    for i, (col1, col2) in enumerate(rows):
        table_rows.append({
            "type": "table_row",
            "table_row": {
                "cells": [
                    [{"type": "text", "text": {"content": col1}}],
                    [{"type": "text", "text": {"content": col2}}],
                ]
            }
        })

    return [
        {
            "type": "table",
            "table": {
                "table_width": 2,
                "has_column_header": True,
                "has_row_header": False,
                "children": table_rows,
            }
        }
    ]

def push_to_notion(name, url, source, schema, stats=None, avatar_url=None, banner_url=None):
    """
    Create a Notion database page.
    - Always sets Name, Platform Link, Source.
    - If stats provided (YouTube only), adds a stats table to the page body.
    """
    props = {}

    # Name
    name_col = resolve_prop_name(schema, "Name")
    props[name_col] = {"title": [{"text": {"content": name}}]}

    # Platform Link (URL column)
    link_col = resolve_prop_name(schema, "Platform Link")
    link_meta = schema.get(link_col, {})
    if link_meta.get("type") == "url":
        props[link_col] = {"url": url}
    else:
        props[link_col] = {"rich_text": [{"text": {"content": url}}]}

    # Subscribers (YouTube only — raw number for the column)
    if stats and stats.get("subscribers") is not None:
        subs_col = resolve_prop_name(schema, "Subscribers")
        if subs_col in schema:
            subs_meta = schema.get(subs_col, {})
            if subs_meta.get("type") == "number":
                props[subs_col] = {"number": stats["subscribers"]}
            else:
                props[subs_col] = {"rich_text": [{"text": {"content": fmt_num(stats["subscribers"])}}]}

    # Source (Select)
    source_col = resolve_prop_name(schema, "Source")
    if source_col in schema:
        props[source_col] = {"select": {"name": source}}

    # Status → Pending
    status_col = resolve_prop_name(schema, "Status")
    if status_col in schema:
        props[status_col] = {"select": {"name": "Pending"}}

    payload = {
        "parent":     {"database_id": DATABASE_ID},
        "properties": props,
    }

    if avatar_url:
        payload["icon"]  = {"type": "external", "external": {"url": avatar_url}}
    if banner_url:
        payload["cover"] = {"type": "external", "external": {"url": banner_url}}

    # YouTube: embed stats table as page body
    if stats:
        payload["children"] = build_stats_table_blocks(stats)

    r = requests.post(
        "https://api.notion.com/v1/pages",
        headers={
            "Authorization":  f"Bearer {NOTION_TOKEN}",
            "Content-Type":   "application/json",
            "Notion-Version": "2022-06-28",
        },
        json=payload
    )
    return r

# ── Display ───────────────────────────────────────────────────

def print_stats(stats):
    bar = "─" * 46
    print(f"\n  {bar}")
    print(f"  {'CHANNEL REPORT':^44}")
    print(f"  {bar}")
    print(f"  {'Channel':<20} {stats['name']}")
    print(f"  {'Subscribers':<20} {fmt_num(stats['subscribers'])}")
    print(f"  {'Total Videos':<20} {stats['total_videos'] or 'N/A'}")
    freq_str = (str(stats['frequency']) + " videos/week") if stats['frequency'] else "N/A"
    vr_str   = (str(stats['vr']) + "%") if stats['vr'] else "N/A"
    er_str   = (str(stats['er']) + "%") if stats['er'] else "N/A"
    print(f"  {'Upload Frequency':<20} {freq_str}")
    print(f"  {'Avg Video Length':<20} {fmt_duration(stats['avg_duration'])}")
    print(f"  {'Avg Views':<20} {fmt_num(stats['avg_views'])}")
    print(f"  {'Avg Likes':<20} {fmt_num(stats['avg_likes'])}")
    print(f"  {'Avg Comments':<20} {fmt_num(stats['avg_comments'])}")
    print(f"  {'View Ratio (VR%)':<20} {vr_str}")
    print(f"  {'Engagement Rate':<20} {er_str}")
    print(f"  {'Platform':<20} YouTube")
    print(f"  {'Link':<20} {stats['channel_url'] or 'N/A'}")
    print(f"  {'Avatar URL':<20} {'✓ found' if stats['avatar_url'] else '✗ not found'}")
    print(f"  {'Banner URL':<20} {'✓ found' if stats['banner_url'] else '✗ not found'}")
    print(f"  {bar}\n")

# ── Main ──────────────────────────────────────────────────────

def main():
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║   MVS Studios · Outreach · Information   ║")
    print("  ╚══════════════════════════════════════════╝")
    print()

    _r = subprocess.run(
        ['osascript', '-e',
         'display dialog "Paste URL (YouTube, X, Discord, Skool):" '
         'default answer "" with title "MVS Studios · Information" '
         'buttons {"Cancel","OK"} default button "OK"'],
        capture_output=True, text=True
    )
    if _r.returncode != 0: sys.exit(0)
    raw_url = _r.stdout.strip().split("text returned:")[-1].strip()
    if not raw_url:
        print("  No URL provided. Exiting.")
        sys.exit(1)

    print()

    # ── Detect platform ───────────────────────────────────────
    source = detect_source(raw_url)
    if not source:
        print("  ✗ Unrecognised URL. Supported platforms: YouTube, X, Discord, Skool.")
        sys.exit(1)

    print(f"  Detected platform: {source}")

    # ── Fetch Notion schema ───────────────────────────────────
    print("  Fetching Notion database schema...")
    schema = get_db_schema()

    # ── YouTube: full stats flow ──────────────────────────────
    if source == "YouTube":
        channel_url = resolve_channel_url(raw_url)

        meta = get_channel_meta(channel_url)
        if not meta:
            print("  ✗ Failed to fetch channel data. Check the URL and try again.")
            sys.exit(1)

        videos = get_video_details(channel_url)

        print("  Computing statistics...")
        stats = compute_stats(meta, videos)

        print_stats(stats)

        page_name = stats["name"]
        print("  Adding page to Notion...")
        r = push_to_notion(
            name       = page_name,
            url        = stats["channel_url"] or raw_url,
            source     = "YouTube",
            schema     = schema,
            stats      = stats,
            avatar_url = stats["avatar_url"],
            banner_url = stats["banner_url"],
        )

    # ── X / Discord / Skool: lightweight entry ────────────────
    else:
        # Use a simple name derived from the URL
        page_name = raw_url.split("//")[-1].split("/")[0]  # e.g. "x.com"

        print(f"  Adding {source} link to Notion (no stats)...")
        r = push_to_notion(
            name   = raw_url,   # full URL as title so it's identifiable
            url    = raw_url,
            source = source,
            schema = schema,
        )

    # ── Result ────────────────────────────────────────────────
    if r.status_code == 200:
        page = r.json()
        page_url = page.get("url", "")
        print(f"\n  ✓ Done! Page added to Notion.")
        print(f"  → {page_url}\n")
    else:
        print(f"\n  ✗ Notion API error ({r.status_code})")
        try:
            err = r.json()
            print(f"     {err.get('code')}: {err.get('message')}")
        except Exception:
            print(f"     {r.text[:400]}")
        sys.exit(1)

if __name__ == "__main__":
    main()