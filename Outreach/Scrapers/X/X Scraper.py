"""
X (Twitter) Follower Post Keyword Scanner
==========================================
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

NOTION_KEY   = os.environ.get("NOTION_KEY", "")
X_SCRAPER_DB   = os.environ.get("X_SCRAPER_DB", "")
NOTION_HEADERS = {
    "Authorization":  f"Bearer {NOTION_KEY}",
    "Content-Type":   "application/json",
    "Notion-Version": "2022-06-28",
}

BOLD   = "\033[1m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
DIM    = "\033[2m"

COOKIES_PATH_FILE = os.path.expanduser("~/.x_scanner_cookies_path")


def log(msg, color=RESET):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{DIM}[{ts}]{RESET} {color}{msg}{RESET}")


def process_and_upload_banner(banner_url):
    """Download banner, blur + darken, upload to 0x0.st, return public URL."""
    try:
        r = requests.get(banner_url, timeout=10)
        if r.status_code != 200:
            return None
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
        log(f"  Banner upload failed: {e}", YELLOW)
        return None


def push_to_notion(username, post_url, text, banner_url=None):
    """Create a row in the X Scraper Notion database."""
    cover_url = process_and_upload_banner(banner_url) if banner_url else None
    payload = {
        "parent": {"database_id": X_SCRAPER_DB},
        "icon": {
            "type": "external",
            "external": {"url": f"https://unavatar.io/twitter/{username}"}
        },
        "properties": {
            "Username": {
                "title": [{"text": {"content": f"@{username}"}}]
            },
            "Text": {
                "rich_text": [{"text": {"content": text[:2000]}}]
            },
            "Post": {
                "url": post_url if post_url else None
            },
        }
    }
    if cover_url:
        payload["cover"] = {"type": "external", "external": {"url": cover_url}}
    if post_url:
        payload["children"] = [
            {
                "object": "block",
                "type": "embed",
                "embed": {"url": post_url}
            }
        ]
    r = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=payload
    )
    if r.status_code == 200:
        log(f"  Pushed @{username} to Notion.", GREEN)
    else:
        log(f"  Notion error {r.status_code}: {r.text[:120]}", YELLOW)


def print_match(username, post_url, text, keyword):
    hi = re.sub(f"({re.escape(keyword)})", f"{BOLD}{GREEN}\\1{RESET}", text, flags=re.IGNORECASE)
    print(f"\n{'─'*60}")
    print(f"{CYAN}{BOLD}@{username}{RESET}  {DIM}{post_url}{RESET}")
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

    BG     = "#1c1c1e"
    CARD   = "#2c2c2e"
    ACCENT = "#0a84ff"
    FG     = "#f2f2f7"
    FG_DIM = "#8e8e93"
    BORDER = "#3a3a3c"
    root.configure(bg=BG)

    tk.Label(root, text="X Keyword Scanner",
             font=("SF Pro Display", 17, "bold"), bg=BG, fg=FG
             ).pack(pady=(24, 2), padx=24)
    tk.Label(root, text="Scan a user's followers for posts matching a keyword",
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
        entry.bind("<FocusIn>",  focus_in)
        entry.bind("<FocusOut>", focus_out)
        entry.pack(fill="x", padx=24, ipady=8)
        return entry, placeholder

    x_entry,  x_ph  = make_entry("X Profile URL or @username",  "https://x.com/username")
    kw_entry, kw_ph = make_entry("Keyword / Phrase",             "e.g. looking for editor")

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

    followers_var = make_num(row, "Followers to Scan", 100)
    posts_var     = make_num(row, "Posts / User",       30)

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
        raw = x_entry.get().strip()
        kw  = kw_entry.get().strip()
        if raw == x_ph or not raw:
            messagebox.showerror("Missing field", "Please enter an X profile URL or @username.")
            return
        if kw == kw_ph or not kw:
            messagebox.showerror("Missing field", "Please enter a keyword to search for.")
            return
        cookie_path = cookie_var.get().strip()
        if not cookie_path:
            messagebox.showerror("Missing field", "Please select your cookies JSON file.")
            return
        if not os.path.exists(cookie_path):
            messagebox.showerror("File not found", f"Cookie file not found:\n{cookie_path}")
            return
        username = raw
        username = re.sub(r"https?://(www\.)?(x|twitter)\.com/", "", username)
        username = username.lstrip("@").split("/")[0].split("?")[0].strip()
        if not username:
            messagebox.showerror("Invalid input", "Could not parse a username from that input.")
            return
        try:
            n_followers = int(followers_var.get())
            n_posts     = int(posts_var.get())
        except ValueError:
            messagebox.showerror("Invalid number", "Followers to Scan and Posts/User must be whole numbers.")
            return
        with open(COOKIES_PATH_FILE, "w") as f:
            f.write(cookie_path)
        result["username"]      = username
        result["keyword"]       = kw
        result["max_followers"] = n_followers
        result["max_posts"]     = n_posts
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
              activebackground="#0071e3", activeforeground="white",
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


async def get_followers(page, username, max_followers):
    url = f"https://x.com/{username}/followers"
    log(f"Opening followers page: {url}", CYAN)
    await page.goto(url, wait_until="domcontentloaded")
    await asyncio.sleep(3)

    log(f"  Landed on: {page.url}", DIM)
    if "login" in page.url or "i/flow" in page.url:
        log("Redirected to login — cookies may be expired. Re-export from Chrome.", RED)
        return []

    try:
        await page.wait_for_selector('[data-testid="UserCell"]', timeout=15000)
    except PlaywrightTimeout:
        title = await page.title()
        log(f"  Page title: {title}", DIM)
        log("Follower cells never loaded — account may be private or not logged in.", RED)
        return []

    followers = []
    seen = set()
    last_count = 0
    stale_rounds = 0

    while len(followers) < max_followers and stale_rounds < 4:
        cells = await page.query_selector_all('[data-testid="UserCell"]')
        for cell in cells:
            link = await cell.query_selector('a[href^="/"]')
            if not link:
                continue
            href = await link.get_attribute("href")
            if not href:
                continue
            parts = href.strip("/").split("/")
            uname = parts[0]
            skip = {"home", "explore", "notifications", "messages", "search",
                    "settings", "i", "login", "logout", "signup", "tos",
                    "privacy", "about", "help", username.lower()}
            if uname and uname not in skip and uname not in seen:
                seen.add(uname)
                followers.append(uname)

        if len(followers) == last_count:
            stale_rounds += 1
        else:
            stale_rounds = 0
            log(f"  Collected {len(followers)} followers...", DIM)
            last_count = len(followers)

        if len(followers) < max_followers:
            await page.evaluate("window.scrollBy(0, 1500)")
            await asyncio.sleep(1.5)

    log(f"Collected {len(followers)} follower usernames", GREEN)
    random.shuffle(followers)
    return followers[:max_followers]


async def scan_user_posts(page, username, keyword, max_posts):
    url = f"https://x.com/{username}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(2)
    except PlaywrightTimeout:
        log(f"  Timeout loading @{username}, skipping", YELLOW)
        return []

    # Grab banner — wait for lazy-load then request highest res
    banner_url = None
    try:
        await page.wait_for_selector('img[src*="profile_banners"]', timeout=5000)
        banner_el = await page.query_selector('img[src*="profile_banners"]')
        if banner_el:
            src = await banner_el.get_attribute("src")
            if src:
                # Strip size suffix to get full resolution
                banner_url = re.sub(r'/\d+x\d+$', '/1500x500', src)
    except Exception:
        pass

    matches = []
    seen_texts = set()
    stale_rounds = 0
    posts_checked = 0

    while posts_checked < max_posts and stale_rounds < 3:
        prev_checked = posts_checked
        articles = await page.query_selector_all('article[data-testid="tweet"]')

        for article in articles:
            try:
                text_el = await article.query_selector('[data-testid="tweetText"]')
                if not text_el:
                    continue
                text = await text_el.inner_text()
                if not text or text in seen_texts:
                    continue
                seen_texts.add(text)
                posts_checked += 1

                if keyword.lower() in text.lower():
                    link_el = await article.query_selector('a[href*="/status/"]')
                    post_url = ""
                    if link_el:
                        href = await link_el.get_attribute("href")
                        post_url = f"https://x.com{href}" if href else ""
                    matches.append((username, post_url, text, banner_url))
            except Exception:
                continue

        if posts_checked == prev_checked:
            stale_rounds += 1
        else:
            stale_rounds = 0

        if posts_checked < max_posts:
            await page.evaluate("window.scrollBy(0, 1200)")
            await asyncio.sleep(1.2)

    return matches


async def run_scan(config):
    username      = config["username"]
    keyword       = config["keyword"]
    max_followers = config["max_followers"]
    max_posts     = config["max_posts"]
    headless      = config["headless"]
    cookie_path   = config["cookie_path"]

    print(f"\n{BOLD}{CYAN}X Follower Keyword Scanner{RESET}")
    print(f"  Target account   : @{username}")
    print(f"  Keyword          : \"{keyword}\"")
    print(f"  Followers to scan: {max_followers}")
    print(f"  Posts/user       : {max_posts}")
    print()

    log(f"Loading cookies from {cookie_path}...", DIM)
    try:
        cookies = load_cookies_from_file(cookie_path)
        names = [c["name"] for c in cookies]
        has_auth = "auth_token" in names
        has_ct0  = "ct0" in names
        log(f"Loaded {len(cookies)} cookies — auth_token: {'YES' if has_auth else 'MISSING'}, ct0: {'YES' if has_ct0 else 'MISSING'}",
            GREEN if (has_auth and has_ct0) else YELLOW)
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
        await page.goto("https://x.com/home", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        logged_in = await page.query_selector('[data-testid="SideNav_AccountSwitcher_Button"]')
        if not logged_in:
            log("Cookies didn't authenticate — please re-export from Chrome and try again.", RED)
            await browser.close()
            sys.exit(1)
        log("Session authenticated.", GREEN)

        log(f"Fetching followers of @{username}...", CYAN)
        followers = await get_followers(page, username, max_followers)

        if not followers:
            await browser.close()
            return

        log(f"\nScanning {len(followers)} followers for keyword: \"{keyword}\"\n", CYAN)

        for i, follower in enumerate(followers, 1):
            log(f"[{i}/{len(followers)}] Scanning @{follower}...", DIM)
            try:
                matches = await scan_user_posts(page, follower, keyword, max_posts)
                if matches:
                    for m in matches:
                        print_match(m[0], m[1], m[2], keyword)
                        push_to_notion(m[0], m[1], m[2], m[3] if len(m) > 3 else None)
                    all_matches.extend(matches)
            except Exception as e:
                log(f"  Error scanning @{follower}: {e}", YELLOW)
            await asyncio.sleep(1.5)

        await browser.close()

    print(f"\n{'='*60}")
    print(f"{BOLD}Scan complete.{RESET}")
    print(f"  Followers scanned : {len(followers)}")
    print(f"  Matching posts    : {len(all_matches)}")
    if all_matches:
        print(f"\n{GREEN}{BOLD}Accounts with matching posts:{RESET}")
        for u, url, _, *_ in all_matches:
            print(f"  @{u}  {DIM}{url}{RESET}")
    print()


def main():
    config = show_config_popup()
    if config is None:
        print("Cancelled.")
        sys.exit(0)
    asyncio.run(run_scan(config))


if __name__ == "__main__":
    main()
