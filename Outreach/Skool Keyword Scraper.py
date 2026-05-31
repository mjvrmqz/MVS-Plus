"""
Skool Community Keyword Scanner
=================================
Scans members of a Skool community and finds posts matching a keyword.

Setup:
  1. Install Cookie-Editor extension in Chrome
  2. Go to skool.com while logged in
  3. Click the extension -> Export -> Export as JSON
  4. Save as ~/skool_cookies.json

Usage:
    python3 "Skool Keyword Scraper.py"
"""

import asyncio
import json
import os
import re
import sys
import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

COOKIES_PATH_FILE = os.path.expanduser("~/.skool_scanner_cookies_path")


def load_cookies_from_file(path):
    with open(path, "r") as f:
        raw = json.load(f)
    cookies = []
    for c in raw:
        cookie = {
            "name":     c.get("name", ""),
            "value":    c.get("value", ""),
            "domain":   c.get("domain", ".skool.com"),
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
    root.title("Skool Keyword Scanner")
    root.resizable(False, False)
    # GUI config: community_url, keyword, max_members, max_posts, headless, cookie_path
    # See full local implementation for complete UI
    root.mainloop()
    return result if result else None


async def get_members(page, community_url, max_members):
    members_url = community_url + "/-/members"
    await page.goto(members_url, wait_until="domcontentloaded")
    await asyncio.sleep(3)
    try:
        await page.wait_for_selector('a[href*="/@"]', timeout=15000)
    except PlaywrightTimeout:
        return []
    members = []; seen = set(); stale_rounds = 0; last_count = 0
    while len(members) < max_members and stale_rounds < 4:
        links = await page.query_selector_all('a[href*="/@"]')
        for link in links:
            href = await link.get_attribute("href")
            if not href: continue
            if href.startswith("/"): href = "https://www.skool.com" + href
            if href not in seen:
                seen.add(href)
                slug = href.split("/@")[-1].split("?")[0]
                members.append({"url": href, "name": slug})
        stale_rounds = 0 if len(members) != last_count else stale_rounds + 1
        last_count = len(members)
        if len(members) < max_members:
            await page.evaluate("window.scrollBy(0, 1500)")
            await asyncio.sleep(1.5)
    return members[:max_members]


async def scan_member_posts(page, member, keyword, community_url, max_posts):
    try:
        await page.goto(member["url"], wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(3)
    except PlaywrightTimeout:
        return []
    matches = []; seen_texts = set(); stale_rounds = 0; posts_checked = 0
    while posts_checked < max_posts and stale_rounds < 3:
        prev = posts_checked
        post_els = await page.query_selector_all(
            '[class*="post"], [class*="feed"], [class*="card"], [class*="entry"], [class*="content"], article'
        )
        for el in post_els:
            try:
                text = (await el.inner_text()).strip()
                if not text or len(text) < 30 or text in seen_texts: continue
                seen_texts.add(text); posts_checked += 1
                if keyword.lower() in text.lower():
                    link_el = await el.query_selector('a[href*="/@"], a[href*="/p/"], a')
                    post_url = member["url"]
                    if link_el:
                        href = await link_el.get_attribute("href")
                        if href: post_url = ("https://www.skool.com" + href) if href.startswith("/") else href
                    matches.append((member["name"], post_url, text))
            except Exception: continue
        stale_rounds = 0 if posts_checked != prev else stale_rounds + 1
        if posts_checked < max_posts:
            await page.evaluate("window.scrollBy(0, 1200)")
            await asyncio.sleep(1.2)
    return matches


async def run_scan(config):
    community_url = config["community_url"]; keyword = config["keyword"]
    max_members = config["max_members"]; max_posts = config["max_posts"]
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
        await page.goto("https://www.skool.com", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        members = await get_members(page, community_url, max_members)
        for member in members:
            try:
                matches = await scan_member_posts(page, member, keyword, community_url, max_posts)
                for m in matches:
                    print(f"{m[0]}  {m[1]}")
            except Exception as e:
                print(f"Error scanning {member['name']}: {e}")
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
