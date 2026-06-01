#!/usr/bin/env python3
"""
MSV Studios · Clips Builder
Paste a YouTube link → pick type → define clips with timestamps & notes
→ pushes everything to Notion with full Breakdown sub-page.
"""

import subprocess, sys, os, io, threading, requests, json, re
import random, tempfile, base64, glob, time
from pathlib import Path

# ── auto-install ───────────────────────────────────────────────────────────────
def pip(*pkgs):
    for p in pkgs:
        subprocess.check_call([sys.executable, "-m", "pip", "install", p, "--break-system-packages", "-q"])

try:
    from PIL import Image
except ImportError:
    pip("Pillow"); from PIL import Image

try:
    import yt_dlp
except ImportError:
    pip("yt-dlp"); import yt_dlp

import tkinter as tk

# ── constants ──────────────────────────────────────────────────────────────────
NOTION_TOKEN = "ntn_U60582391564u7rDIIxeSyYXMD7aOqEaawu30A8D3wUag7"
DATABASE_ID  = "35c1691964b4800f9d73d71d01cb5e2f"
NOTION_HDR   = {
    "Authorization":  f"Bearer {NOTION_TOKEN}",
    "Content-Type":   "application/json",
    "Notion-Version": "2022-06-28",
}
IMGUR_CLIENT = "546c25a59c58ad7"

BG     = "#0e0e0e"
BG2    = "#161616"
BG3    = "#1c1c1c"
BORD   = "#2c2c2c"
FG     = "#e8e8e8"
FG2    = "#999999"
FG3    = "#555555"
ACCENT = "#ff0033"
GREEN  = "#37c337"
FONT   = "Helvetica Neue"

# ── helpers ────────────────────────────────────────────────────────────────────

def parse_ts(s):
    """Parse timestamp string → int seconds. Accepts ss, mm:ss, hh:mm:ss."""
    s = str(s).strip()
    parts = s.split(":")
    try:
        if len(parts) == 1: return int(float(parts[0]))
        if len(parts) == 2: return int(parts[0]) * 60 + int(float(parts[1]))
        if len(parts) == 3: return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
    except Exception:
        pass
    raise ValueError(f"Invalid timestamp '{s}' — use ss, mm:ss or hh:mm:ss")

def secs_to_hms(s):
    h, r = divmod(int(s), 3600)
    m, s2 = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s2:02d}" if h else f"{m:02d}:{s2:02d}"

def run_ff(args, timeout=300):
    r = subprocess.run(["ffmpeg"] + args, capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg: " + r.stderr.decode()[-400:])

def upload_imgur_bytes(data):
    """Upload image/GIF bytes to imgur → URL."""
    b64 = base64.b64encode(data).decode()
    r = requests.post(
        "https://api.imgur.com/3/image",
        headers={"Authorization": f"Client-ID {IMGUR_CLIENT}"},
        data={"image": b64, "type": "base64"},
        timeout=90,
    )
    r.raise_for_status()
    j = r.json()
    if j.get("success"): return j["data"]["link"]
    raise RuntimeError(f"Imgur: {j.get('data',{}).get('error', j)}")

def upload_imgur_video(filepath):
    """Upload mp4 via multipart → URL."""
    with open(filepath, "rb") as f:
        r = requests.post(
            "https://api.imgur.com/3/upload",
            headers={"Authorization": f"Client-ID {IMGUR_CLIENT}"},
            files={"video": (Path(filepath).name, f, "video/mp4")},
            timeout=180,
        )
    r.raise_for_status()
    j = r.json()
    if j.get("success"): return j["data"]["link"]
    raise RuntimeError(f"Imgur video: {j}")

def upload_notion_file(filepath):
    """Upload video file directly to Notion → file upload ID."""
    name = Path(filepath).name
    # Step 1: create upload
    r = requests.post(
        "https://api.notion.com/v1/file-uploads",
        headers={**NOTION_HDR, "Content-Type": "application/json"},
        json={"filename": name, "content_type": "video/mp4"},
        timeout=30,
    )
    r.raise_for_status()
    upload = r.json()
    print("Notion file-upload response:", upload)
    upload_id  = upload.get("id")
    upload_url = upload.get("upload_url")
    if not upload_id or not upload_url:
        raise RuntimeError(f"Notion file-upload failed: {upload}")
    # Step 2: send file bytes
    with open(filepath, "rb") as f:
        r2 = requests.put(
            upload_url,
            headers={"Authorization": f"Bearer {NOTION_TOKEN}"},
            data=f,
            timeout=300,
        )
        r2.raise_for_status()
    return upload_id

def get_video_info(url):
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        return ydl.extract_info(url, download=False)

def get_channel_avatar(channel_url):
    """Scrape channel page for avatar URL."""
    try:
        hdrs = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        r = requests.get(channel_url, headers=hdrs, timeout=15)
        for pat in [
            r'"avatar":\{"thumbnails":\[\{"url":"([^"]+)"',
            r'"channelAvatarUrl":"([^"]+)"',
        ]:
            m = re.search(pat, r.text)
            if m:
                u = m.group(1)
                return ("https:" + u) if u.startswith("//") else u
    except Exception:
        pass
    return None

def download_full_low(url, out_dir):
    """Download full video at lowest quality. Returns file path."""
    tmpl = os.path.join(out_dir, "full.%(ext)s")
    subprocess.run(
        [sys.executable, "-m", "yt_dlp",
         "-f", "worst[ext=mp4]/worst",
         "-o", tmpl, "--no-playlist", "-q", url],
        check=True, timeout=600,
    )
    for f in os.listdir(out_dir):
        if f.startswith("full."):
            return os.path.join(out_dir, f)
    raise RuntimeError("Low-quality video download failed")

def download_clip_file(url, start, end, out_dir, idx):
    """Download time-ranged clip. Returns file path."""
    tmpl  = os.path.join(out_dir, f"clip{idx}.%(ext)s")
    s_hms = secs_to_hms(start)
    e_hms = secs_to_hms(end)
    subprocess.run(
        [sys.executable, "-m", "yt_dlp",
         "--download-sections", f"*{s_hms}-{e_hms}",
         "--force-keyframes-at-cuts",
         "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
         "-o", tmpl, "--no-playlist", "-q", url],
        check=True, timeout=300,
    )
    for f in os.listdir(out_dir):
        if f.startswith(f"clip{idx}."):
            return os.path.join(out_dir, f)
    raise RuntimeError(f"Clip {idx} download failed")

def make_gif(video_path, duration):
    """
    Create a 5-second GIF from 5 random 1-second segments.
    Blurred + darkened. Returns bytes, guaranteed < 5 MB.
    """
    max_t = max(float(duration) - 1.5, 0.5)

    # Pick 5 non-overlapping start times (2 s spacing)
    segs = []
    for _ in range(500):
        t = round(random.uniform(0, max_t), 3)
        if all(abs(t - s) >= 2.0 for s in segs):
            segs.append(t)
        if len(segs) == 5:
            break
    while len(segs) < 5:
        segs.append(round(random.uniform(0, max_t), 3))
    segs.sort()

    def build_fc(scale, fps):
        trims  = [f"[0:v]trim=start={t:.3f}:duration=1,setpts=PTS-STARTPTS[v{i}]"
                  for i, t in enumerate(segs)]
        labels = "".join(f"[v{i}]" for i in range(5))
        return (
            ";".join(trims)
            + f";{labels}concat=n=5:v=1:a=0[cat]"
            + f";[cat]fps={fps},scale={scale}:-2:flags=lanczos,"
              "boxblur=luma_radius=8:luma_power=1,"
              "curves=all='0/0 1/0.38'[out]"
        )

    with tempfile.TemporaryDirectory() as tmp:
        gif_path     = os.path.join(tmp, "out.gif")
        palette_path = os.path.join(tmp, "pal.png")

        for scale, fps in [(540, 10), (360, 8)]:
            fc = build_fc(scale, fps)
            try:
                # Two-pass palette GIF
                run_ff(["-y", "-i", video_path,
                        "-filter_complex", fc + ";[out]palettegen=max_colors=128[pal]",
                        "-map", "[pal]", palette_path])
                run_ff(["-y", "-i", video_path, "-i", palette_path,
                        "-filter_complex", fc + ";[out][1:v]paletteuse=dither=bayer[final]",
                        "-map", "[final]", gif_path])
            except Exception:
                # Single-pass fallback
                try:
                    run_ff(["-y", "-i", video_path,
                            "-filter_complex", fc, "-map", "[out]", gif_path])
                except Exception:
                    continue

            data = open(gif_path, "rb").read()
            if len(data) <= 5 * 1024 * 1024:
                return data

        # Last resort: whatever size we have
        return open(gif_path, "rb").read()

# ── Notion API ─────────────────────────────────────────────────────────────────

def n_post(path, body):
    r = requests.post(f"https://api.notion.com/v1{path}",
                      headers=NOTION_HDR, json=body, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Notion POST {path} → {r.status_code}: {r.text[:300]}")
    return r.json()

def n_patch(path, body):
    r = requests.patch(f"https://api.notion.com/v1{path}",
                       headers=NOTION_HDR, json=body, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Notion PATCH {path} → {r.status_code}: {r.text[:300]}")
    return r.json()

def n_get(path):
    r = requests.get(f"https://api.notion.com/v1{path}",
                     headers=NOTION_HDR, timeout=30)
    return r.json()

def title_prop(db_id):
    db = n_get(f"/databases/{db_id}")
    for k, v in db.get("properties", {}).items():
        if v.get("type") == "title": return k
    return "Name"

# ── main pipeline ──────────────────────────────────────────────────────────────

def run_pipeline(url, info, avatar_url, category, clips, status):
    vid_id    = info.get("id", "")
    vid_title = info.get("title", "Untitled")
    thumb_url = info.get("thumbnail", "")
    duration  = float(info.get("duration") or 60)

    prop = title_prop(DATABASE_ID)

    # ── 1. Main database page ──────────────────────────────────────────────────
    status("Creating main page…", 0.10)
    main_body = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            prop:   {"title":  [{"text": {"content": vid_title}}]},
            "Type": {"select": {"name": category}},
        },
    }
    if avatar_url:
        main_body["icon"] = {"type": "external", "external": {"url": avatar_url}}
    main    = n_post("/pages", main_body)
    main_id = main["id"]

    # ── 2. Thumbnail on main page ──────────────────────────────────────────────
    status("Adding thumbnail…", 0.15)
    n_patch(f"/blocks/{main_id}/children", {"children": [
        {"object": "block", "type": "image",
         "image": {"type": "external", "external": {"url": thumb_url}}}
    ]})

    # ── 3. Breakdown sub-page ──────────────────────────────────────────────────
    status("Creating Breakdown page…", 0.20)
    breakdown_body = {
        "parent":     {"page_id": main_id},
        "properties": {"title": {"title": [{"text": {"content": "Breakdown"}}]}},
    }
    if avatar_url:
        breakdown_body["icon"] = {"type": "external", "external": {"url": avatar_url}}
    breakdown    = n_post("/pages", breakdown_body)
    breakdown_id = breakdown["id"]

    with tempfile.TemporaryDirectory() as tmp:
        # ── 4. Download full video (low quality) for GIF ───────────────────────
        status("Downloading video for GIF…", 0.25)
        video_path = download_full_low(url, tmp)

        # ── 5. Generate GIF ────────────────────────────────────────────────────
        status("Generating GIF cover…", 0.35)
        gif_data = make_gif(video_path, duration)

        status("Uploading GIF…", 0.45)
        gif_url = upload_imgur_bytes(gif_data)

        # ── 6. Set Breakdown page cover ────────────────────────────────────────
        status("Setting Breakdown cover…", 0.50)
        n_patch(f"/pages/{breakdown_id}", {
            "cover": {"type": "external", "external": {"url": gif_url}}
        })

        # ── 7. Callout with embedded video ─────────────────────────────────────
        status("Building Breakdown content…", 0.55)
        callout_resp = n_patch(f"/blocks/{breakdown_id}/children", {"children": [
            {
                "object": "block", "type": "callout",
                "callout": {
                    "rich_text": [],
                    "icon":  {"type": "emoji", "emoji": "🎬"},
                    "color": "default",
                    "children": [
                        {"object": "block", "type": "video",
                         "video": {"type": "external", "external": {"url": url}}}
                    ],
                }
            }
        ]})

        # ── 8. Inline "Clips" database ─────────────────────────────────────────
        status("Creating Clips database…", 0.60)
        clips_db    = n_post("/databases", {
            "parent":     {"page_id": breakdown_id},
            "is_inline":  True,
            "title":      [{"text": {"content": "Clips"}}],
            "properties": {
                "Name":  {"title": {}},
                "Link":  {"url": {}},
                "Notes": {"rich_text": {}},
            },
            "views": [{"type": "gallery", "name": "Gallery", "layout": "gallery"}],
        })
        clips_db_id = clips_db["id"]
        time.sleep(0.6)  # let Notion register the new database

        # ── 9. One page per clip ───────────────────────────────────────────────
        for i, clip in enumerate(clips):
            n = i + 1
            status(f"Processing Clip {n} of {len(clips)}…",
                   0.65 + i / len(clips) * 0.30)

            start, end, notes = clip["start"], clip["end"], clip["notes"]
            clip_name = clip["name"] if clip["name"] else f"Clip {n}"

            # Download clip segment
            clip_path = download_clip_file(url, start, end, tmp, n)

            # Upload clip to imgur
            clip_url = upload_imgur_video(clip_path)

            # YouTube timestamp deep-link
            yt_ts = f"https://www.youtube.com/watch?v={vid_id}&t={start}s"

            page_body = {
                "parent": {"database_id": clips_db_id},
                "properties": {
                    "Name":  {"title":     [{"text": {"content": clip_name}}]},
                    "Link":  {"url":       yt_ts},
                    "Notes": {"rich_text": [{"text": {"content": notes}}] if notes else []},
                },
                "children": [
                    {"object": "block", "type": "video",
                     "video": {"type": "external", "external": {"url": clip_url}}}
                ],
            }
            if avatar_url:
                page_body["icon"] = {"type": "external", "external": {"url": avatar_url}}

            n_post("/pages", page_body)

    return vid_title

# ── GUI ────────────────────────────────────────────────────────────────────────

class ClipRow:
    def __init__(self, parent, idx, on_filled):
        self.idx        = idx
        self._triggered = False

        self.frame = tk.Frame(parent, bg=BG3,
                              highlightthickness=1, highlightbackground=BORD)
        self.frame.pack(fill="x", pady=(0, 8))

        # label + name field
        lbl_row = tk.Frame(self.frame, bg=BG3)
        lbl_row.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(lbl_row, text=f"Clip {idx}",
                 font=(FONT, 11, "bold"), bg=BG3, fg=FG).pack(side="left")
        tk.Label(lbl_row, text="Name", font=(FONT, 10),
                 bg=BG3, fg=FG2).pack(side="left", padx=(16, 6))
        self.name_var = tk.StringVar()
        tk.Entry(lbl_row, textvariable=self.name_var, width=22,
                 bg=BG2, fg=FG, insertbackground=FG,
                 font=(FONT, 11), bd=0,
                 highlightthickness=1, highlightbackground=BORD,
                 relief="flat").pack(side="left", ipady=4)

        # timestamps row
        ts = tk.Frame(self.frame, bg=BG3)
        ts.pack(fill="x", padx=12)

        self.start_var = tk.StringVar()
        self.end_var   = tk.StringVar()

        for label, var in [("Start", self.start_var), ("End", self.end_var)]:
            tk.Label(ts, text=label, font=(FONT, 10), bg=BG3, fg=FG2,
                     width=5, anchor="w").pack(side="left")
            tk.Entry(ts, textvariable=var, width=10,
                     bg=BG2, fg=FG, insertbackground=FG,
                     font=(FONT, 11), bd=0,
                     highlightthickness=1, highlightbackground=BORD,
                     relief="flat").pack(side="left", padx=(0, 18), ipady=5)
            var.trace_add("write", lambda *_, cb=on_filled: self._check(cb))

        tk.Label(ts, text="ss  or  mm:ss", font=(FONT, 9),
                 bg=BG3, fg=FG3).pack(side="left")

        # notes
        tk.Label(self.frame, text="Notes", font=(FONT, 10),
                 bg=BG3, fg=FG2).pack(anchor="w", padx=12, pady=(8, 2))
        self.notes = tk.Text(self.frame, height=3,
                             bg=BG2, fg=FG, insertbackground=FG,
                             font=(FONT, 11), bd=0, padx=8, pady=6,
                             highlightthickness=1, highlightbackground=BORD,
                             relief="flat")
        self.notes.pack(fill="x", padx=12, pady=(0, 10))

    def _check(self, callback):
        if self._triggered: return
        if self.start_var.get().strip() and self.end_var.get().strip():
            self._triggered = True
            callback()

    def data(self):
        return {
            "start": self.start_var.get().strip(),
            "end":   self.end_var.get().strip(),
            "notes": self.notes.get("1.0", "end-1c").strip(),
            "name":  self.name_var.get().strip(),
        }


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MSV Studios · Clips")
        self.configure(bg=BG)
        self.geometry("580x720")
        self.resizable(True, True)
        self._cat       = tk.StringVar(value="")
        self._clip_rows = []
        self._busy      = False
        self._build()

    def _build(self):
        # ── header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg="#0a0a0a", height=46)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Clips Builder", font=(FONT, 13, "bold"),
                 bg="#0a0a0a", fg=FG).place(x=18, y=12)
        tk.Label(hdr, text="MSV Studios", font=(FONT, 10),
                 bg="#0a0a0a", fg=FG3).place(relx=1.0, x=-18, y=15, anchor="ne")

        # ── scrollable body ───────────────────────────────────────────────────
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(outer, bg=BG, bd=0, highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient="vertical", command=self._canvas.yview)
        self._body = tk.Frame(self._canvas, bg=BG)

        self._body.bind("<Configure>",
                        lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))

        self._win_id = self._canvas.create_window((0, 0), window=self._body, anchor="nw")
        self._canvas.configure(yscrollcommand=vsb.set)
        self._canvas.bind("<Configure>",
                          lambda e: self._canvas.itemconfig(self._win_id, width=e.width))

        self._canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._canvas.bind_all("<MouseWheel>",
                              lambda e: self._canvas.yview_scroll(-(e.delta // 120), "units"))

        PAD = 18

        # ── URL ───────────────────────────────────────────────────────────────
        tk.Label(self._body, text="YouTube URL", font=(FONT, 11),
                 bg=BG, fg=FG2).pack(anchor="w", padx=PAD, pady=(18, 4))
        self._url = tk.StringVar()
        tk.Entry(self._body, textvariable=self._url,
                 bg=BG2, fg=FG, insertbackground=FG, font=(FONT, 12),
                 bd=0, highlightthickness=1, highlightbackground=BORD,
                 relief="flat").pack(fill="x", padx=PAD, ipady=9)

        # ── Type ──────────────────────────────────────────────────────────────
        tk.Label(self._body, text="Type", font=(FONT, 11),
                 bg=BG, fg=FG2).pack(anchor="w", padx=PAD, pady=(16, 6))
        cat_row = tk.Frame(self._body, bg=BG)
        cat_row.pack(anchor="w", padx=PAD)
        self._cat_btns = {}
        for c in ("Business", "Technical", "Storytelling"):
            btn = tk.Button(cat_row, text=c, font=(FONT, 11), bd=0, relief="flat",
                            padx=14, pady=7, cursor="hand2",
                            command=lambda x=c: self._pick_cat(x))
            btn.pack(side="left", padx=(0, 8))
            self._cat_btns[c] = btn
        self._refresh_cats()

        # ── Clips ─────────────────────────────────────────────────────────────
        tk.Frame(self._body, bg=BORD, height=1).pack(fill="x", padx=PAD, pady=(18, 0))
        tk.Label(self._body, text="Clips", font=(FONT, 12, "bold"),
                 bg=BG, fg=FG).pack(anchor="w", padx=PAD, pady=(10, 10))
        self._clips_frame = tk.Frame(self._body, bg=BG)
        self._clips_frame.pack(fill="x", padx=PAD)
        self._add_clip_row()  # start with Clip 1

        # ── Status + submit ───────────────────────────────────────────────────
        tk.Frame(self._body, bg=BORD, height=1).pack(fill="x", padx=PAD, pady=(14, 0))
        bot = tk.Frame(self._body, bg=BG)
        bot.pack(fill="x", padx=PAD, pady=(10, 22))

        self._status_var = tk.StringVar(value="")
        tk.Label(bot, textvariable=self._status_var, font=(FONT, 10),
                 bg=BG, fg=FG2, anchor="w").pack(fill="x", pady=(0, 6))

        self._prog = tk.Canvas(bot, bg=BG3, height=3, bd=0, highlightthickness=0)
        self._prog.pack(fill="x", pady=(0, 10))

        self._btn = tk.Button(bot, text="Push to Notion →",
                              font=(FONT, 12, "bold"),
                              bg=ACCENT, fg="white", bd=0, relief="flat",
                              padx=20, pady=10, cursor="hand2",
                              activebackground="#cc0029", activeforeground="white",
                              command=self._submit)
        self._btn.pack(anchor="e")

    # ── cat toggle ─────────────────────────────────────────────────────────────
    def _pick_cat(self, cat):
        self._cat.set(cat)
        self._refresh_cats()

    def _refresh_cats(self):
        sel = self._cat.get()
        for c, btn in self._cat_btns.items():
            btn.config(bg=ACCENT if c == sel else BG3,
                       fg="white" if c == sel else FG2)

    # ── dynamic clips ──────────────────────────────────────────────────────────
    def _add_clip_row(self):
        idx = len(self._clip_rows) + 1
        row = ClipRow(self._clips_frame, idx, on_filled=self._add_clip_row)
        self._clip_rows.append(row)
        self._body.update_idletasks()
        self._canvas.yview_moveto(1.0)

    # ── progress bar ───────────────────────────────────────────────────────────
    def _set_status(self, msg, p=None):
        self._status_var.set(msg)
        if p is not None:
            self._prog.update_idletasks()
            w = max(self._prog.winfo_width(), 1)
            self._prog.delete("all")
            self._prog.create_rectangle(0, 0, w,     3, fill=BG3,    outline="")
            self._prog.create_rectangle(0, 0, w * p, 3, fill=ACCENT, outline="")

    # ── submit ─────────────────────────────────────────────────────────────────
    def _submit(self):
        if self._busy: return

        url = self._url.get().strip()
        if not url:
            self._set_status("⚠  Enter a YouTube URL"); return
        cat = self._cat.get()
        if not cat:
            self._set_status("⚠  Select a type"); return

        clips = []
        for row in self._clip_rows:
            d = row.data()
            if not d["start"] and not d["end"]: continue
            if not d["start"] or not d["end"]:
                self._set_status(f"⚠  Clip {row.idx}: fill in both timestamps"); return
            try:
                s = parse_ts(d["start"])
                e = parse_ts(d["end"])
            except ValueError as ex:
                self._set_status(f"⚠  Clip {row.idx}: {ex}"); return
            if e <= s:
                self._set_status(f"⚠  Clip {row.idx}: end must be after start"); return
            clips.append({"start": s, "end": e, "notes": d["notes"], "name": d["name"]})

        if not clips:
            self._set_status("⚠  Add at least one clip with timestamps"); return

        self._busy = True
        self._btn.config(state="disabled", bg="#2a2a2a", fg=FG3)
        threading.Thread(target=self._run, args=(url, cat, clips), daemon=True).start()

    def _run(self, url, cat, clips):
        def st(msg, p=None):
            self.after(0, lambda m=msg, pr=p: self._set_status(m, pr))
        try:
            st("Fetching video info…", 0.04)
            info = get_video_info(url)

            st("Fetching channel avatar…", 0.08)
            ch_url = info.get("channel_url") or info.get("uploader_url", "")
            avatar = get_channel_avatar(ch_url) if ch_url else None

            title = run_pipeline(url, info, avatar, cat, clips, st)

            self.after(0, lambda: self._set_status(f'✓  Added "{title}" to Notion!', 1.0))
            self.after(0, lambda: self._btn.config(state="normal", bg=GREEN, fg="white", text="✓ Done"))
        except Exception as e:
            err = str(e)[:120]
            self.after(0, lambda: self._set_status(f"✗  {err}", 0.0))
            self.after(0, lambda: self._btn.config(
                state="normal", bg=ACCENT, fg="white", text="Push to Notion →"))
            self._busy = False


if __name__ == "__main__":
    App().mainloop()