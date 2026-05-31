"""
X (Twitter) Follower Post Keyword Scanner
==========================================
Scans followers of a given X account for posts matching a keyword.
Results are pushed to Notion (X Scraper DB) with cover images.

Usage:
    source ~/scripts-env/bin/activate
    pip install requests pycryptodome pillow
    python3 "X Keyword Scraper.py"
"""

import asyncio
import json
import os
import random
import re
import sys
import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import requests
import io
from PIL import Image, ImageFilter

NOTION_TOKEN   = "ntn_U60582391564u7rDIIxeSyYXMD7aOqEaawu30A8D3wUag7"
X_SCRAPER_DB   = "3601691964b4805e9a96fa8e17d0de76"
NOTION_HEADERS = {
    "Authorization":  f"Bearer {NOTION_TOKEN}",
    "Content-Type":   "application/json",
    "Notion-Version": "2022-06-28",
}

COOKIES_PATH_FILE = os.path.expanduser("~/.x_scanner_cookies_path")


def process_and_upload_banner(banner_url):
    try:
        r = requests.get(banner_url, timeout=10)
        if r.status_code != 200: return None
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        img = img.filter(ImageFilter.GaussianBlur(radius=10))
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 140))
        img = Image.alpha_composite(img, overlay).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        upload = requests.post(
            "https://litterbox.catbox.moe/resources/internals/api.php",
            data={"reqtype": "fileupload", "time": "72h"},
            files={"fileToUpload": ("cover.jpg", buf, "image/jpeg")},
            timeout=15
        )
        if upload.status_code == 200 and upload.text.startswith("http"):
            return upload.text.strip()
        return None
    except Exception as e:
        return None


def push_to_notion(username, post_url, text, banner_url=None):
    cover_url = process_and_upload_banner(banner_url) if banner_url else None
    payload = {
        "parent": {"database_id": X_SCRAPER_DB},
        "icon": {"type": "external", "external": {"url": f"https://unavatar.io/twitter/{username}"}},
        "properties": {
            "Username": {"title": [{"text": {"content": f"@{username}"}}]},
            "Text":     {"rich_text": [{"text": {"content": text[:2000]}}]},
            "Post":     {"url": post_url if post_url else None},
        }
    }
    if cover_url:
        payload["cover"] = {"type": "external", "external": {"url": cover_url}}
    if post_url:
        payload["children"] = [{"object": "block", "type": "embed", "embed": {"url": post_url}}]
    requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS, json=payload)


def load_cookies_from_file(path):
    with open(path, "r") as f:
        raw = json.load(f)
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
    return cookies


def show_config_popup():
    result = {}
    root = tk.Tk()
    root.title("X Keyword Scanner")
    root.resizable(False, False)
    BG = "#1c1c1e"; CARD = "#2c2c2e"; ACCENT = "#0a84ff"; FG = "#f2f2f7"; FG_DIM = "#8e8e93"; BORDER = "#3a3a3c"
    root.configure(bg=BG)
    # ... GUI setup omitted for brevity. See full implementation in local file.
    # Key config keys: username, keyword, max_followers, max_posts, headless, cookie_path
    root.mainloop()
    return result if result else None


async def get_followers(page, username, max_followers):
    url = f"https://x.com/{username}/followers"
    await page.goto(url, wait_until="domcontentloaded")
    await asyncio.sleep(3)
    followers = []
    seen = set()
    stale_rounds = 0; last_count = 0
    while len(followers) < max_followers and stale_rounds < 4:
        cells = await page.query_selector_all('[data-testid="UserCell"]')
        for cell in cells:
            link = await cell.query_selector('a[href^="/"]')
            if not link: continue
            href = await link.get_attribute("href")
            if not href: continue
            uname = href.strip("/").split("/")[0]
            skip = {"home","explore","notifications","messages","search","settings","i","login","logout","signup",username.lower()}
            if uname and uname not in skip and uname not in seen:
                seen.add(uname); followers.append(uname)
        stale_rounds = 0 if len(followers) != last_count else stale_rounds + 1
        last_count = len(followers)
        if len(followers) < max_followers:
            await page.evaluate("window.scrollBy(0, 1500)")
            await asyncio.sleep(1.5)
    return followers[:max_followers]


async def scan_user_posts(page, username, keyword, max_posts):
    await page.goto(f"https://x.com/{username}", wait_until="domcontentloaded", timeout=15000)
    await asyncio.sleep(2)
    banner_url = None
    try:
        await page.wait_for_selector('img[src*="profile_banners"]', timeout=5000)
        el = await page.query_selector('img[src*="profile_banners"]')
        if el:
            src = await el.get_attribute("src")
            if src: banner_url = re.sub(r'/\d+x\d+$', '/1500x500', src)
    except Exception: pass
    matches = []; seen_texts = set(); stale_rounds = 0; posts_checked = 0
    while posts_checked < max_posts and stale_rounds < 3:
        prev = posts_checked
        articles = await page.query_selector_all('article[data-testid="tweet"]')
        for article in articles:
            try:
                text_el = await article.query_selector('[data-testid="tweetText"]')
                if not text_el: continue
                text = await text_el.inner_text()
                if not text or text in seen_texts: continue
                seen_texts.add(text); posts_checked += 1
                if keyword.lower() in text.lower():
                    link_el = await article.query_selector('a[href*="/status/"]')
                    post_url = ""
                    if link_el:
                        href = await link_el.get_attribute("href")
                        post_url = f"https://x.com{href}" if href else ""
                    matches.append((username, post_url, text, banner_url))
            except Exception: continue
        stale_rounds = 0 if posts_checked != prev else stale_rounds + 1
        if posts_checked < max_posts:
            await page.evaluate("window.scrollBy(0, 1200)")
            await asyncio.sleep(1.2)
    return matches


async def run_scan(config):
    username = config["username"]; keyword = config["keyword"]
    max_followers = config["max_followers"]; max_posts = config["max_posts"]
    headless = config["headless"]; cookie_path = config["cookie_path"]
    cookies = load_cookies_from_file(cookie_path)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        for cookie in cookies:
            try: await context.add_cookies([cookie])
            except Exception: pass
        page = await context.new_page()
        await page.goto("https://x.com/home", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        followers = await get_followers(page, username, max_followers)
        for follower in followers:
            try:
                matches = await scan_user_posts(page, follower, keyword, max_posts)
                for m in matches:
                    push_to_notion(m[0], m[1], m[2], m[3] if len(m) > 3 else None)
            except Exception as e:
                print(f"Error scanning @{follower}: {e}")
            await asyncio.sleep(1.5)
        await browser.close()


def main():
    config = show_config_popup()
    if config is None:
        print("Cancelled.")
        sys.exit(0)
    asyncio.run(run_scan(config))


if __name__ == "__main__":
    main()
