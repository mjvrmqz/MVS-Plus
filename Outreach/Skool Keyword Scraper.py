"""
Skool Community Keyword Scanner
=================================
Scans members of a Skool community and finds posts matching a keyword.

Setup (one time):
  1. Install "Cookie-Editor" extension in Chrome
  2. Go to skool.com while logged in
  3. Click the extension -> Export -> Export as JSON
  4. Save the file somewhere e.g. ~/skool_cookies.json

Usage:
    source ~/scripts-env/bin/activate
    python3 "Skool Keytag Scraper.py"
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

BOLD   = "\033[1m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
DIM    = "\033[2m"

COOKIES_PATH_FILE = os.path.expanduser("~/.skool_scanner_cookies_path")


def log(msg, color=RESET):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{DIM}[{ts}]{RESET} {color}{msg}{RESET}")


def print_match(name, post_url, text, keyword):
    hi = re.sub(f"({re.escape(keyword)})", f"{BOLD}{GREEN}\\1{RESET}", text, flags=re.IGNORECASE)
    print(f"\n{'─'*60}")
    print(f"{CYAN}{BOLD}{name}{RESET}  {DIM}{post_url}{RESET}")
    print(f"{hi[:400]}{'...' if len(text) > 400 else ''}")
    print(f"{'─'*60}")


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

    BG     = "#1c1c1e"
    CARD   = "#2c2c2e"
    ACCENT = "#6c4df6"
    FG     = "#f2f2f7"
    FG_DIM = "#8e8e93"
    BORDER = "#3a3a3c"
    root.configure(bg=BG)

    tk.Label(root, text="Skool Keyword Scanner",
             font=("SF Pro Display", 17, "bold"), bg=BG, fg=FG
             ).pack(pady=(24, 2), padx=24)
    tk.Label(root, text="Scan a community's members for posts matching a keyword",
             font=("SF Pro Text", 11), bg=BG, fg=FG_DIM
             ).pack(pady=(0, 18), padx=24)

    def make_entry(label_text, placeholder):
        tk.Label(root, text=label_text,
                 font=("SF Pro Text", 11, "bold"), bg=BG, fg=FG_DIM, anchor="w"
                 ).pack(fill="x", padx=24, pady=(6, 2))
        entry = tk.Entry(root, font=("SF Pro Text", 13), bg=CARD, fg=FG_DIM,
                         insertbackground=FG, relief="flat", bd=0,
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=ACCENT)
        entry.insert(0, placeholder)
        def focus_in(e):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.config(fg=FG)
        def focus_out(e):
            if entry.get().strip() == "":
                entry.insert(0, placeholder)
                entry.config(fg=FG_DIM)
        entry.bind("<FocusIn>", focus_in)
        entry.bind("<FocusOut>", focus_out)
        entry.pack(fill="x", padx=24, ipady=8)
        return entry, placeholder

    community_entry, community_ph = make_entry("Skool Community URL", "https://www.skool.com/your-community")
    kw_entry, kw_ph = make_entry("Keyword / Phrase", "e.g. looking for editor")

    tk.Label(root, text="Cookies JSON File",
             font=("SF Pro Text", 11, "bold"), bg=BG, fg=FG_DIM, anchor="w"
             ).pack(fill="x", padx=24, pady=(6, 2))
    cookie_row = tk.Frame(root, bg=BG)
    cookie_row.pack(fill="x", padx=24)

    saved_path = ""
    if os.path.exists(COOKIES_PATH_FILE):
        with open(COOKIES_PATH_FILE) as f:
            saved_path = f.read().strip()
    cookie_var = tk.StringVar(value=saved_path or "")
    tk.Entry(cookie_row, textvariable=cookie_var, font=("SF Pro Text", 12),
             bg=CARD, fg=FG, insertbackground=FG, relief="flat", bd=0,
             highlightthickness=1, highlightbackground=BORDER,
             highlightcolor=ACCENT).pack(side="left", fill="x", expand=True, ipady=7)

    def browse_cookies():
        path = filedialog.askopenfilename(
            title="Select cookies JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.path.expanduser("~"))
        if path:
            cookie_var.set(path)

    tk.Button(cookie_row, text="Browse", command=browse_cookies,
              font=("SF Pro Text", 11), bg=CARD, fg=FG_DIM,
              activebackground="#3a3a3c", activeforeground=FG,
              relief="flat", bd=0, padx=12, pady=7,
              cursor="hand2").pack(side="left", padx=(6, 0))

    row = tk.Frame(root, bg=BG)
    row.pack(fill="x", padx=24, pady=(14, 0))

    def make_num(parent, label, default):
        f = tk.Frame(parent, bg=BG)
        f.pack(side="left", padx=(0, 20))
        tk.Label(f, text=label, font=("SF Pro Text", 10, "bold"),
                 bg=BG, fg=FG_DIM).pack(anchor="w")
        sv = tk.StringVar(value=str(default))
        tk.Entry(f, textvariable=sv, width=6, font=("SF Pro Text", 12),
                 bg=CARD, fg=FG, insertbackground=FG, relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT, justify="center").pack(ipady=6)
        return sv

    max_mem_var = make_num(row, "Max Members", 100)
    posts_var   = make_num(row, "Posts / Member", 20)

    hf = tk.Frame(row, bg=BG)
    hf.pack(side="left")
    tk.Label(hf, text="Hide Browser", font=("SF Pro Text", 10, "bold"),
             bg=BG, fg=FG_DIM).pack(anchor="w")
    headless_var = tk.BooleanVar(value=False)
    tk.Checkbutton(hf, variable=headless_var, bg=BG,
                   activebackground=BG, selectcolor=CARD).pack(anchor="w", pady=4)

    tk.Frame(root, bg=BORDER, height=1).pack(fill="x", pady=(20, 0))
    btn_row = tk.Frame(root, bg="#232325")
    btn_row.pack(fill="x")

    def on_cancel():
        root.destroy()

    def on_run():
        raw = community_entry.get().strip()
        kw  = kw_entry.get().strip()
        if raw == community_ph or not raw:
            messagebox.showerror("Missing field", "Please enter a Skool community URL.")
            return
        if kw == kw_ph or not kw:
            messagebox.showerror("Missing field", "Please enter a keyword to search for.")
            return
        cookie_path = cookie_var.get().strip()
        if not cookie_path:
            messagebox.showerror("Missing field", "Please select your Skool cookies JSON file.")
            return
        if not os.path.exists(cookie_path):
            messagebox.showerror("File not found", f"Cookie file not found:\n{cookie_path}")
            return
        community_url = raw.rstrip("/")
        if not community_url.startswith("http"):
            community_url = "https://www.skool.com/" + community_url.lstrip("/")
        try:
            max_mem  = int(max_mem_var.get())
            max_post = int(posts_var.get())
        except ValueError:
            messagebox.showerror("Invalid number", "Max Members and Posts/Member must be whole numbers.")
            return
        with open(COOKIES_PATH_FILE, "w") as f:
            f.write(cookie_path)
        result["community_url"] = community_url
        result["keyword"]       = kw
        result["max_members"]   = max_mem
        result["max_posts"]     = max_post
        result["headless"]      = headless_var.get()
        result["cookie_path"]   = cookie_path
        root.destroy()

    tk.Button(btn_row, text="Cancel", command=on_cancel,
              font=("SF Pro Text", 13), bg="#232325", fg=FG_DIM,
              activebackground="#2c2c2e", activeforeground=FG,
              relief="flat", bd=0, padx=24, pady=14,
              cursor="hand2").pack(side="left")
    tk.Button(btn_row, text="▶  Start Scan", command=on_run,
              font=("SF Pro Text", 13, "bold"), bg=ACCENT, fg="white",
              activebackground="#5a3de0", activeforeground="white",
              relief="flat", bd=0, padx=24, pady=14,
              cursor="hand2").pack(side="right")

    root.update_idletasks()
    w = root.winfo_reqwidth()
    h = root.winfo_reqheight()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
    root.mainloop()
    return result if result else None


async def get_members(page, community_url, max_members):
    members_url = community_url + "/-/members"
    log(f"Opening members page: {members_url}", CYAN)
    await page.goto(members_url, wait_until="domcontentloaded")
    await asyncio.sleep(3)

    log(f"  Landed on: {page.url}", DIM)
    if "login" in page.url or "sign" in page.url:
        log("Redirected to login — cookies may be expired.", RED)
        return []

    await asyncio.sleep(2)
    all_links = await page.query_selector_all('a[href]')
    sample = []
    for l in all_links[:60]:
        h = await l.get_attribute('href')
        if h and ('skool.com' in h or h.startswith('/')):
            sample.append(h)
    log(f"  Sample hrefs: {sample[:15]}", DIM)

    try:
        await page.wait_for_selector('a[href*="/@"]', timeout=15000)
    except PlaywrightTimeout:
        title = await page.title()
        log(f"  Page title: {title}", DIM)
        log("Member cards never loaded — community may be private or URL is wrong.", RED)
        return []

    members = []
    seen = set()
    last_count = 0
    stale_rounds = 0

    while len(members) < max_members and stale_rounds < 4:
        links = await page.query_selector_all('a[href*="/@"]')
        for link in links:
            href = await link.get_attribute("href")
            if not href:
                continue
            if href.startswith("/"):
                href = "https://www.skool.com" + href
            if href not in seen:
                seen.add(href)
                try:
                    # Username is in the href itself e.g. /@ana-v-3766
                    slug = href.split("/@")[-1].split("?")[0]
                    name = slug
                except Exception:
                    name = href
                members.append({"url": href, "name": name})

        if len(members) == last_count:
            stale_rounds += 1
        else:
            stale_rounds = 0
            log(f"  Collected {len(members)} members...", DIM)
            last_count = len(members)

        if len(members) < max_members:
            await page.evaluate("window.scrollBy(0, 1500)")
            await asyncio.sleep(1.5)

    log(f"Collected {len(members)} members", GREEN)
    return members[:max_members]


async def scan_member_posts(page, member, keyword, community_url, max_posts, debug=False):
    profile_url = member["url"]
    try:
        await page.goto(profile_url, wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(3)
    except PlaywrightTimeout:
        log(f"  Timeout loading {member['name']}, skipping", YELLOW)
        return []

    # Debug: dump raw text blocks on first member so we can see what's on the page
    if debug:
        all_els = await page.query_selector_all('div, p, article, section, span')
        log(f"  DEBUG — {len(all_els)} elements on profile page. Samples:", DIM)
        dumped = 0
        for el in all_els:
            try:
                cls = await el.get_attribute('class') or ''
                t = (await el.inner_text()).strip()
                if 30 < len(t) < 400:
                    log(f"    [{cls[:60]}] {t[:120]}", DIM)
                    dumped += 1
                    if dumped >= 12:
                        break
            except Exception:
                continue

    matches = []
    seen_texts = set()
    stale_rounds = 0
    posts_checked = 0

    while posts_checked < max_posts and stale_rounds < 3:
        prev_checked = posts_checked

        # Try every reasonable Skool post container selector
        post_els = await page.query_selector_all(
            '[class*="post"], [class*="feed"], [class*="card"], '
            '[class*="entry"], [class*="content"], [class*="message"], '
            '[class*="rich"], [class*="body"], article, '
            '[data-testid], [class*="activity"]'
        )

        for el in post_els:
            try:
                text = (await el.inner_text()).strip()
                if not text or len(text) < 30 or text in seen_texts:
                    continue
                seen_texts.add(text)
                posts_checked += 1
                if keyword.lower() in text.lower():
                    link_el = await el.query_selector('a[href*="/@"], a[href*="/p/"], a')
                    post_url = profile_url
                    if link_el:
                        href = await link_el.get_attribute("href")
                        if href:
                            post_url = ("https://www.skool.com" + href) if href.startswith("/") else href
                    matches.append((member["name"], post_url, text))
            except Exception:
                continue

        if posts_checked == prev_checked:
            stale_rounds += 1
        else:
            stale_rounds = 0

        if posts_checked < max_posts:
            await page.evaluate("window.scrollBy(0, 1200)")
            await asyncio.sleep(1.2)

    log(f"  Checked {posts_checked} elements, {len(matches)} matched", DIM)
    return matches


async def run_scan(config):
    community_url = config["community_url"]
    keyword       = config["keyword"]
    max_members   = config["max_members"]
    max_posts     = config["max_posts"]
    headless      = config["headless"]
    cookie_path   = config["cookie_path"]

    print(f"\n{BOLD}{CYAN}Skool Keyword Scanner{RESET}")
    print(f"  Community    : {community_url}")
    print(f"  Keyword      : \"{keyword}\"")
    print(f"  Max members  : {max_members}")
    print(f"  Posts/member : {max_posts}")
    print()

    log(f"Loading cookies from {cookie_path}...", DIM)
    try:
        cookies = load_cookies_from_file(cookie_path)
        log(f"Loaded {len(cookies)} cookies.", GREEN)
    except Exception as e:
        log(f"Failed to load cookies: {e}", RED)
        sys.exit(1)

    all_matches = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
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
        await page.goto("https://www.skool.com", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        if "login" in page.url or "sign" in page.url:
            log("Not authenticated — cookies may be expired. Re-export from Chrome.", RED)
            await browser.close()
            sys.exit(1)
        log("Session authenticated.", GREEN)

        log(f"Fetching members of {community_url}...", CYAN)
        members = await get_members(page, community_url, max_members)

        if not members:
            log("No members found. Check the community URL and try again.", RED)
            await browser.close()
            return

        log(f"\nScanning {len(members)} members for keyword: \"{keyword}\"\n", CYAN)

        for i, member in enumerate(members, 1):
            log(f"[{i}/{len(members)}] Scanning {member['name']}...", DIM)
            try:
                matches = await scan_member_posts(page, member, keyword, community_url, max_posts)
                if matches:
                    for m in matches:
                        print_match(*m, keyword)
                    all_matches.extend(matches)
            except Exception as e:
                log(f"  Error scanning {member['name']}: {e}", YELLOW)
            await asyncio.sleep(1.5)

        await browser.close()

    print(f"\n{'='*60}")
    print(f"{BOLD}Scan complete.{RESET}")
    print(f"  Members scanned : {len(members)}")
    print(f"  Matching posts  : {len(all_matches)}")
    if all_matches:
        print(f"\n{GREEN}{BOLD}Members with matching posts:{RESET}")
        for name, url, _ in all_matches:
            print(f"  {name}  {DIM}{url}{RESET}")
    print()


def main():
    config = show_config_popup()
    if config is None:
        print("Cancelled.")
        sys.exit(0)
    asyncio.run(run_scan(config))


if __name__ == "__main__":
    main()
