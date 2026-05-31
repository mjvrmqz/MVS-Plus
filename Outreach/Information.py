#!/usr/bin/env python3
# Information.py · MVS Studios / Outreach
# Paste a URL (YouTube, X, Discord, Skool) → push to Notion Screening DB.
# YouTube links also pull channel stats into the page body.

import subprocess, json, sys, os, re, requests, statistics
from datetime import datetime

NOTION_TOKEN  = "ntn_U60582391564u7rDIIxeSyYXMD7aOqEaawu30A8D3wUag7"
DATABASE_ID   = "28d1691964b48065b59ec1f0b293f91f"
YTDLP         = "/Library/Frameworks/Python.framework/Versions/3.13/bin/yt-dlp"
SAMPLE_VIDEOS = 15

def detect_source(url):
    url_lower = url.lower()
    if re.search(r'(youtube\.com|youtu\.be)', url_lower): return "YouTube"
    if re.search(r'(twitter\.com|x\.com)', url_lower):   return "X"
    if re.search(r'discord\.com|discord\.gg', url_lower): return "Discord"
    if re.search(r'skool\.com', url_lower):               return "Skool"
    return None

def fmt_num(n):
    if n is None: return "N/A"
    if n >= 1_000_000: return f"{n/1_000_000:.2f}M"
    if n >= 1_000:     return f"{n/1_000:.1f}K"
    return str(n)

def fmt_duration(secs):
    if not secs: return "N/A"
    secs = int(secs); h, rem = divmod(secs, 3600); m, s = divmod(rem, 60)
    if h: return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"

def run(args, label=""):
    if label: print(f"  {label}", end="", flush=True)
    r = subprocess.run([YTDLP] + args, capture_output=True, text=True)
    if label: print(" ✓")
    return r.stdout.strip()

# Full implementation: resolve_channel_url, get_channel_meta, get_video_details,
# extract_thumbnails, compute_stats, push_to_notion, main…
# See full local file for complete implementation.

if __name__ == "__main__":
    pass
