#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
#  Forward.py  ·  MVS Studios / Outreach
#  Finds all "Forwarded" entries in Screening → copies them
#  into the Outreach database with a calendar date/time picker.
# ─────────────────────────────────────────────────────────────

import sys, json, requests, tkinter as tk
from tkinter import ttk, font as tkfont
from datetime import datetime, timedelta
from calendar import monthcalendar, month_abbr

# ── Config ────────────────────────────────────────────────────
NOTION_TOKEN    = os.environ.get("NOTION_KEY", "")
SCREENING_DB_ID = "28d1691964b48065b59ec1f0b293f91f"
OUTREACH_DB_ID  = "28d1691964b480a88260e3871d01824c"

HEADERS = {
    "Authorization":  f"Bearer {NOTION_KEY}",
    "Content-Type":   "application/json",
    "Notion-Version": "2022-06-28",
}

# Colours — Apple-ish light/neutral palette
BG        = "#f2f2f7"   # iOS systemGroupedBackground
SURFACE   = "#ffffff"
CARD      = "#f2f2f7"
ACCENT    = "#007aff"   # iOS blue
ACCENT2   = "#5856d6"
TEXT      = "#1c1c1e"
SUBTEXT   = "#8e8e93"
DAY_SEL   = "#007aff"
DAY_HOV   = "#e5f0ff"
DAY_TODAY = "#ff3b30"   # red dot for today
WHITE     = "#ffffff"

# ── Notion helpers ────────────────────────────────────────────

def query_forwarded():
    payload = {
        "filter": {
            "property": "Status",
            "select":   {"equals": "Forwarded"},
        }
    }
    r = requests.post(
        f"https://api.notion.com/v1/databases/{SCREENING_DB_ID}/query",
        headers=HEADERS, json=payload,
    )
    r.raise_for_status()
    return r.json().get("results", [])

def get_page_name(page):
    try:
        parts = page["properties"]["Name"]["title"]
        return "".join(t["plain_text"] for t in parts).strip()
    except (KeyError, IndexError):
        return "Untitled"

def get_platform_link(page):
    try:
        return page["properties"]["Platform Link"]["url"] or ""
    except KeyError:
        return ""

def get_source(page):
    try:
        return page["properties"]["Source"]["select"]["name"]
    except (KeyError, TypeError):
        return None

def get_page_icon_cover(page):
    """Extract icon URL and cover URL from a Notion page object."""
    icon  = None
    cover = None
    try:
        icon_obj = page.get("icon") or {}
        if icon_obj.get("type") == "external":
            icon = icon_obj["external"]["url"]
        elif icon_obj.get("type") == "file":
            icon = icon_obj["file"]["url"]
    except Exception:
        pass
    try:
        cover_obj = page.get("cover") or {}
        if cover_obj.get("type") == "external":
            cover = cover_obj["external"]["url"]
        elif cover_obj.get("type") == "file":
            cover = cover_obj["file"]["url"]
    except Exception:
        pass
    return icon, cover


def fmt_notion_dt(dt):
    """ISO 8601 date+time — Notion requires timezone, use UTC offset."""
    import time as _time
    if _time.daylight and _time.localtime().tm_isdst:
        offset_sec = -_time.altzone
    else:
        offset_sec = -_time.timezone
    sign = "+" if offset_sec >= 0 else "-"
    h, m = divmod(abs(offset_sec) // 60, 60)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + f"{sign}{h:02d}:{m:02d}"

def fmt_notion_date(dt):
    return dt.strftime("%Y-%m-%d")

def platform_link_to_mode(url):
    """Map a platform URL to a Contact Mode option name.
    Only returns a value when it matches a known existing option.
    Returns None for anything else so we don't corrupt the field.
    """
    if not url:
        return None
    u = url.lower()
    if "x.com" in u or "twitter.com" in u:
        return "X"
    if "mail" in u or "email" in u:
        return "Email"
    return None  # don't send unknown URLs as option names

def create_outreach_entry(name, platform_link, start_dt, end_dt, source=None, icon_url=None, cover_url=None):
    a1_start = start_dt + timedelta(days=2)
    a2_start = start_dt + timedelta(days=4)
    a3_start = start_dt + timedelta(days=6)

    date_initiated = {"start": fmt_notion_dt(start_dt)}
    if end_dt:
        date_initiated["end"] = fmt_notion_dt(end_dt)
        # Carry the same duration forward for A1/A2/A3
        duration   = end_dt - start_dt
        a1_end     = a1_start + duration
        a2_end     = a2_start + duration
        a3_end     = a3_start + duration
        a1_date    = {"start": fmt_notion_dt(a1_start), "end": fmt_notion_dt(a1_end)}
        a2_date    = {"start": fmt_notion_dt(a2_start), "end": fmt_notion_dt(a2_end)}
        a3_date    = {"start": fmt_notion_dt(a3_start), "end": fmt_notion_dt(a3_end)}
    else:
        a1_date = {"start": fmt_notion_dt(a1_start)}
        a2_date = {"start": fmt_notion_dt(a2_start)}
        a3_date = {"start": fmt_notion_dt(a3_start)}

    # A1/A2/A3 keep the same time-of-day as start, just shifted by days
    props = {
        "Name":           {"title": [{"text": {"content": name}}]},
        "Date Initiated": {"date": date_initiated},
        "A1":             {"date": a1_date},
        "A2":             {"date": a2_date},
        "A3":             {"date": a3_date},
    }

    if source:
        props["Source"] = {"select": {"name": source}}

    if platform_link:
        props["Contact Mode"] = {"rich_text": [{"text": {"content": platform_link}}]}

    payload = {"parent": {"database_id": OUTREACH_DB_ID}, "properties": props}

    if icon_url:
        payload["icon"]  = {"type": "external", "external": {"url": icon_url}}
    if cover_url:
        payload["cover"] = {"type": "external", "external": {"url": cover_url}}

    r = requests.post(
        "https://api.notion.com/v1/pages",
        headers=HEADERS,
        json=payload,
    )
    return r

# ── Calendar picker UI ────────────────────────────────────────

class DateTimePicker(tk.Toplevel):
    """
    A styled calendar + time picker.
    Returns (start_dt, end_dt) via self.result.
    end_dt may be None if the user leaves end time blank.
    """

    def __init__(self, parent, entry_name):
        super().__init__(parent)
        self.result     = None
        self.entry_name = entry_name

        today         = datetime.today()
        self._year    = today.year
        self._month   = today.month
        self._sel_day = today.day

        self.title("MVS Studios · Forward")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._build()
        self._center()
        self.grab_set()
        self.focus_force()

    # ── layout ──────────────────────────────────────────────

    def _build(self):
        root = self

        # ── Header ──────────────────────────────────────────
        hdr = tk.Frame(root, bg=SURFACE, pady=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Forward to Outreach", bg=SURFACE,
                 fg=TEXT, font=("-size", 15, "-weight", "bold")).pack()
        tk.Label(hdr, text=self.entry_name, bg=SURFACE,
                 fg=SUBTEXT, font=("-size", 12)).pack(pady=(3, 0))
        tk.Frame(root, bg="#d1d1d6", height=1).pack(fill="x")  # separator

        body = tk.Frame(root, bg=BG, padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # ── Calendar card ────────────────────────────────────
        cal_card = tk.Frame(body, bg=SURFACE, bd=0, relief="flat",
                            padx=14, pady=12)
        cal_card.pack(fill="x", pady=(0, 12))

        # Month nav
        nav = tk.Frame(cal_card, bg=SURFACE)
        nav.pack(fill="x", pady=(0, 8))
        tk.Button(nav, text="<", bg=SURFACE, fg=ACCENT,
                  font=("-size", 13, "-weight", "bold"),
                  bd=0, highlightthickness=0,
                  activebackground=SURFACE, activeforeground=ACCENT,
                  cursor="hand2", command=self._prev_month).pack(side="left")
        self._month_lbl = tk.Label(nav, text="", bg=SURFACE, fg=TEXT,
                                   font=("-size", 13, "-weight", "bold"), width=14)
        self._month_lbl.pack(side="left", expand=True)
        tk.Button(nav, text=">", bg=SURFACE, fg=ACCENT,
                  font=("-size", 13, "-weight", "bold"),
                  bd=0, highlightthickness=0,
                  activebackground=SURFACE, activeforeground=ACCENT,
                  cursor="hand2", command=self._next_month).pack(side="right")

        # Day-of-week headers
        dow_frame = tk.Frame(cal_card, bg=SURFACE)
        dow_frame.pack(fill="x")
        for i, d in enumerate(["Mo","Tu","We","Th","Fr","Sa","Su"]):
            tk.Label(dow_frame, text=d, bg=SURFACE, fg=SUBTEXT,
                     font=("-size", 10), width=4).grid(
                row=0, column=i, pady=(0, 6))

        # Day grid
        self._day_frame = tk.Frame(cal_card, bg=SURFACE)
        self._day_frame.pack(fill="x")
        self._day_btns  = {}
        self._render_calendar()

        # ── Time card ────────────────────────────────────────
        time_card = tk.Frame(body, bg=SURFACE, padx=14, pady=12)
        time_card.pack(fill="x", pady=(0, 12))

        tk.Label(time_card, text="Time Range", bg=SURFACE, fg=TEXT,
                 font=("-size", 12, "-weight", "bold")).pack(anchor="w", pady=(0, 8))

        row = tk.Frame(time_card, bg=SURFACE)
        row.pack(fill="x")

        # Start time
        s_col = tk.Frame(row, bg=SURFACE)
        s_col.pack(side="left", expand=True, fill="x", padx=(0, 8))
        tk.Label(s_col, text="Start", bg=SURFACE, fg=SUBTEXT,
                 font=("-size", 10)).pack(anchor="w")
        s_inner = tk.Frame(s_col, bg=CARD, padx=6, pady=4)
        s_inner.pack(fill="x", pady=(3, 0))
        self._start_h = self._spin(s_inner, 0, 23, 9)
        tk.Label(s_inner, text=":", bg=CARD, fg=TEXT,
                 font=("-size", 14, "-weight", "bold")).pack(side="left", padx=2)
        self._start_m = self._spin(s_inner, 0, 59, 0)

        # End time
        e_col = tk.Frame(row, bg=SURFACE)
        e_col.pack(side="left", expand=True, fill="x", padx=(8, 0))
        tk.Label(e_col, text="End (optional)", bg=SURFACE, fg=SUBTEXT,
                 font=("-size", 10)).pack(anchor="w")
        e_inner = tk.Frame(e_col, bg=CARD, padx=6, pady=4)
        e_inner.pack(fill="x", pady=(3, 0))
        self._end_h = self._spin(e_inner, 0, 23, 10)
        tk.Label(e_inner, text=":", bg=CARD, fg=TEXT,
                 font=("-size", 14, "-weight", "bold")).pack(side="left", padx=2)
        self._end_m = self._spin(e_inner, 0, 59, 0)

        self._no_end = tk.BooleanVar(value=False)
        tk.Checkbutton(time_card, text="No end time",
                       variable=self._no_end,
                       bg=SURFACE, fg=SUBTEXT,
                       selectcolor="#e9e9eb",
                       activebackground=SURFACE,
                       font=("-size", 10),
                       command=self._toggle_end).pack(anchor="w", pady=(6, 0))

        # ── Confirm button ───────────────────────────────────
        tk.Frame(body, bg="#d1d1d6", height=1).pack(fill="x", pady=(4, 8))
        btn = tk.Button(body, text="Confirm",
                        bg=ACCENT, fg=WHITE,
                        font=("-size", 13, "-weight", "bold"),
                        bd=0, highlightthickness=0,
                        padx=20, pady=9,
                        activebackground="#0062cc",
                        activeforeground=WHITE,
                        cursor="hand2",
                        command=self._confirm)
        btn.pack(fill="x")

        cancel = tk.Button(body, text="Cancel",
                           bg=BG, fg=ACCENT,
                           font=("-size", 12),
                           bd=0, highlightthickness=0,
                           pady=7,
                           activebackground=BG,
                           activeforeground="#0062cc",
                           cursor="hand2",
                           command=self._cancel)
        cancel.pack(fill="x")

    def _spin(self, parent, lo, hi, init):
        """A simple +/- spinner that returns a StringVar."""
        var   = tk.StringVar(value=f"{init:02d}")
        pbg   = parent.cget("bg")
        frame = tk.Frame(parent, bg=pbg)
        frame.pack(side="left")

        def dec():
            v = int(var.get())
            var.set(f"{(v - 1) % (hi + 1):02d}")
        def inc():
            v = int(var.get())
            var.set(f"{(v + 1) % (hi + 1):02d}")

        col = tk.Frame(frame, bg=pbg)
        col.pack(side="left")
        tk.Button(col, text="▲", bg=pbg, fg=SUBTEXT, bd=0,
                  font=("-size", 8), highlightthickness=0,
                  activebackground=pbg, activeforeground=ACCENT,
                  cursor="hand2", command=inc).pack()
        tk.Label(col, textvariable=var, bg=pbg, fg=TEXT,
                 font=("-size", 15, "-weight", "bold"), width=2).pack()
        tk.Button(col, text="▼", bg=pbg, fg=SUBTEXT, bd=0,
                  font=("-size", 8), highlightthickness=0,
                  activebackground=pbg, activeforeground=ACCENT,
                  cursor="hand2", command=dec).pack()
        return var

    def _render_calendar(self):
        for w in self._day_frame.winfo_children():
            w.destroy()
        self._day_btns.clear()

        self._month_lbl.config(
            text=f"{month_abbr[self._month]}  {self._year}"
        )
        today = datetime.today()
        weeks = monthcalendar(self._year, self._month)

        for r, week in enumerate(weeks):
            for c, day in enumerate(week):
                if day == 0:
                    tk.Label(self._day_frame, text="", bg=SURFACE,
                             width=3, height=1).grid(row=r, column=c)
                    continue

                is_today = (day == today.day and
                            self._month == today.month and
                            self._year == today.year)
                is_sel   = (day == self._sel_day)

                bg = DAY_SEL if is_sel else (DAY_TODAY if is_today else SURFACE)
                fg = WHITE   if (is_sel or is_today) else TEXT

                lbl = str(day)
                btn = tk.Button(
                    self._day_frame, text=lbl,
                    bg=bg, fg=fg, bd=0, width=3, height=1,
                    font=("-size", 12, "-weight", "bold" if is_sel else "normal"),
                    highlightthickness=0,
                    activebackground=DAY_HOV, activeforeground=ACCENT,
                    cursor="hand2",
                    command=lambda d=day: self._select_day(d),
                )
                btn.grid(row=r, column=c, padx=2, pady=2)
                self._day_btns[day] = btn

    def _select_day(self, day):
        self._sel_day = day
        self._render_calendar()

    def _prev_month(self):
        if self._month == 1:
            self._month = 12; self._year -= 1
        else:
            self._month -= 1
        self._sel_day = 1
        self._render_calendar()

    def _next_month(self):
        if self._month == 12:
            self._month = 1; self._year += 1
        else:
            self._month += 1
        self._sel_day = 1
        self._render_calendar()

    def _toggle_end(self):
        pass  # visual-only for now; we check the var in _confirm

    def _confirm(self):
        start_dt = datetime(
            self._year, self._month, self._sel_day,
            int(self._start_h.get()), int(self._start_m.get())
        )
        end_dt = None
        if not self._no_end.get():
            end_dt = datetime(
                self._year, self._month, self._sel_day,
                int(self._end_h.get()), int(self._end_m.get())
            )

        self.result = (start_dt, end_dt)
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

    def _center(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


def prompt_datetime(root, entry_name):
    picker = DateTimePicker(root, entry_name)
    root.wait_window(picker)
    if picker.result is None:
        print("  Cancelled.")
        sys.exit(0)
    return picker.result  # (start_dt, end_dt)

# ── Main ──────────────────────────────────────────────────────

def main():
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║   MVS Studios · Outreach · Forward       ║")
    print("  ╚══════════════════════════════════════════╝")
    print()

    print("  Querying Screening database for 'Forwarded' entries...")
    pages = query_forwarded()

    if not pages:
        print("  No entries with Status = 'Forwarded' found.")
        sys.exit(0)

    print(f"  Found {len(pages)} forwarded entr{'y' if len(pages) == 1 else 'ies'}.\n")

    # Build a hidden root so Toplevel windows work
    root = tk.Tk()
    root.withdraw()
    root.configure(bg=BG)

    results = []
    for page in pages:
        name          = get_page_name(page)
        platform_link = get_platform_link(page)
        source        = get_source(page)

        icon_url, cover_url = get_page_icon_cover(page)

        print(f"  ─── {name}")
        if platform_link:
            print(f"      Platform Link  : {platform_link}")

        start_dt, end_dt = prompt_datetime(root, name)

        print(f"      Start          : {start_dt.strftime('%Y-%m-%d %H:%M')}")
        if end_dt:
            print(f"      End            : {end_dt.strftime('%Y-%m-%d %H:%M')}")
        print(f"      A1             : {(start_dt + timedelta(days=2)).strftime('%Y-%m-%d')}")
        print(f"      A2             : {(start_dt + timedelta(days=4)).strftime('%Y-%m-%d')}")
        print(f"      A3             : {(start_dt + timedelta(days=6)).strftime('%Y-%m-%d')}")

        print("      Adding to Outreach...", end="", flush=True)
        r = create_outreach_entry(name, platform_link, start_dt, end_dt, source, icon_url, cover_url)

        if r.status_code == 200:
            page_url = r.json().get("url", "")
            print(" ✓")
            print(f"      → {page_url}")
            results.append((name, True, page["id"]))
        else:
            print(f" ✗ ({r.status_code})")
            print(f"      Raw: {r.text[:600]}")
            results.append((name, False, None))

        print()

    root.destroy()

    # Clear "Forwarded" status on successfully processed Screening entries
    for name, success, page_id in results:
        if success and page_id:
            print(f"  Clearing Forwarded tag: {name}...", end="", flush=True)
            patch = requests.patch(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=HEADERS,
                json={"properties": {"Status": {"select": None}}},
            )
            print(" ✓" if patch.status_code == 200 else f" ✗ ({patch.status_code})")

    ok  = sum(1 for _, s, _ in results if s)
    bad = len(results) - ok
    print(f"\n  Done — {ok} added, {bad} failed.\n")

if __name__ == "__main__":
    main()
