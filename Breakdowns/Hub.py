#!/usr/bin/env python3
"""
MVS Studios · Hub
=================
Unified web app combining Upload Frame, Upload Clip, and Upload Lesson.
Run locally: python Hub.py  (opens at http://localhost:5000)

Env vars (put in a .env file next to this script, or set them manually):
  NOTION_KEY, INSPIRATION_DB_ID, CLIPS_DB_ID, LESSONS_DB_ID
"""

import subprocess, sys, os, io, threading, requests, json, re
import random, tempfile, base64, time, uuid
from pathlib import Path
from flask import Flask, request, jsonify, Response

# ── auto-install ───────────────────────────────────────────────────────────────
def pip(*pkgs):
    for p in pkgs:
        subprocess.check_call([sys.executable, "-m", "pip", "install", p, "--break-system-packages", "-q"])

try:
    from PIL import Image, ImageFilter, ImageEnhance
except ImportError:
    pip("Pillow"); from PIL import Image, ImageFilter, ImageEnhance

try:
    import yt_dlp
except ImportError:
    pip("yt-dlp"); import yt_dlp

try:
    from dotenv import load_dotenv
except ImportError:
    pip("python-dotenv"); from dotenv import load_dotenv

# Load .env file if present (safe no-op if missing)
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# ── config ─────────────────────────────────────────────────────────────────────
NOTION_KEY       = os.environ.get("NOTION_KEY", "")
INSPIRATION_DB   = os.environ.get("INSPIRATION_DB_ID", "")
CLIPS_DB         = os.environ.get("CLIPS_DB_ID", "")
LESSONS_DB       = os.environ.get("LESSONS_DB_ID", "")
IMGUR_CLIENT     = "546c25a59c58ad7"

NOTION_HDR = {
    "Authorization":  f"Bearer {NOTION_KEY}",
    "Content-Type":   "application/json",
    "Notion-Version": "2022-06-28",
}

VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm", ".mxf", ".wmv")

# ── shared helpers ─────────────────────────────────────────────────────────────

def upload_imgur_bytes(data, mime="image/jpeg"):
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

def make_blurred_cover(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
    th = int(w * 2 / 5)
    if th < h:
        top = (h - th) // 2
        img = img.crop((0, top, w, top + th))
    img = img.resize((1500, 600), Image.LANCZOS)
    img = img.filter(ImageFilter.GaussianBlur(radius=18))
    img = ImageEnhance.Brightness(img).enhance(0.38)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return buf.getvalue()

def n_post(path, body):
    r = requests.post(f"https://api.notion.com/v1{path}", headers=NOTION_HDR, json=body, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Notion POST {path} → {r.status_code}: {r.text[:300]}")
    return r.json()

def n_patch(path, body):
    r = requests.patch(f"https://api.notion.com/v1{path}", headers=NOTION_HDR, json=body, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Notion PATCH {path} → {r.status_code}: {r.text[:300]}")
    return r.json()

def n_get(path):
    r = requests.get(f"https://api.notion.com/v1{path}", headers=NOTION_HDR, timeout=30)
    return r.json()

def get_title_prop(db_id):
    db = n_get(f"/databases/{db_id}")
    for k, v in db.get("properties", {}).items():
        if v.get("type") == "title": return k
    return "Name"

def get_next_number(db_id, prefix):
    payload = {"filter": {"property": "title", "title": {"starts_with": prefix}}}
    r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query",
                      headers=NOTION_HDR, json=payload)
    if r.status_code != 200: return 1
    nums = []
    for p in r.json().get("results", []):
        for prop in p.get("properties", {}).values():
            if prop.get("type") == "title":
                for t in prop.get("title", []):
                    name = t.get("plain_text", "")
                    if name.startswith(prefix):
                        try: nums.append(int(name[len(prefix):].strip()))
                        except ValueError: pass
    return max(nums) + 1 if nums else 1

# ── Upload Frame logic ─────────────────────────────────────────────────────────

def handle_frame(img_bytes):
    orig_url    = upload_imgur_bytes(img_bytes)
    cover_bytes = make_blurred_cover(img_bytes)
    cover_url   = upload_imgur_bytes(cover_bytes)
    label       = f"Inspiration {get_next_number(INSPIRATION_DB, 'Inspiration ')}"
    prop        = get_title_prop(INSPIRATION_DB)
    payload     = {
        "parent":     {"database_id": INSPIRATION_DB},
        "cover":      {"type": "external", "external": {"url": cover_url}},
        "properties": {prop: {"title": [{"text": {"content": label}}]}},
        "children":   [{"object": "block", "type": "image",
                         "image": {"type": "external", "external": {"url": orig_url}}}],
    }
    r = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HDR, json=payload)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Notion {r.status_code}: {r.text[:80]}")
    return label

# ── Upload Clip logic ──────────────────────────────────────────────────────────

def extract_first_frame(video_path):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-vframes", "1", "-q:v", "2", tmp_path],
            capture_output=True, timeout=30
        )
        if result.returncode != 0 or not os.path.isfile(tmp_path):
            raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()[:200]}")
        return Image.open(tmp_path).copy()
    finally:
        if os.path.isfile(tmp_path): os.unlink(tmp_path)

def make_video_cover(video_path):
    img = extract_first_frame(video_path).convert("RGB")
    w, h = img.size
    target_ratio = 1500 / 600
    src_ratio = w / h
    if src_ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    img = img.resize((1500, 600), Image.LANCZOS)
    img = img.filter(ImageFilter.GaussianBlur(radius=18))
    img = ImageEnhance.Brightness(img).enhance(0.38)
    for quality in (88, 75, 60, 45):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality)
        if buf.tell() < 5 * 1024 * 1024: break
    return buf.getvalue()

def handle_clip(video_bytes, filename):
    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name
    try:
        cover_bytes = make_video_cover(tmp_path)
        cover_url   = upload_imgur_bytes(cover_bytes)
        label       = f"Inspiration {get_next_number(CLIPS_DB, 'Inspiration ')}"
        prop        = get_title_prop(CLIPS_DB)
        payload     = {
            "parent":     {"database_id": CLIPS_DB},
            "cover":      {"type": "external", "external": {"url": cover_url}},
            "properties": {prop: {"title": [{"text": {"content": label}}]}},
            "children":   [{"object": "block", "type": "paragraph",
                             "paragraph": {"rich_text": [{"type": "text", "text": {"content": filename}}]}}],
        }
        r = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HDR, json=payload)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Notion {r.status_code}: {r.text[:80]}")
        return label
    finally:
        os.unlink(tmp_path)

# ── Upload Lesson logic ────────────────────────────────────────────────────────

def parse_ts(s):
    s = str(s).strip()
    parts = s.split(":")
    try:
        if len(parts) == 1: return int(float(parts[0]))
        if len(parts) == 2: return int(parts[0]) * 60 + int(float(parts[1]))
        if len(parts) == 3: return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
    except Exception: pass
    raise ValueError(f"Invalid timestamp '{s}'")

def secs_to_hms(s):
    h, r = divmod(int(s), 3600)
    m, s2 = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s2:02d}" if h else f"{m:02d}:{s2:02d}"

def run_ff(args, timeout=300):
    r = subprocess.run(["ffmpeg"] + args, capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg: " + r.stderr.decode()[-400:])

def get_video_info(url):
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        return ydl.extract_info(url, download=False)

def get_channel_avatar(channel_url):
    try:
        hdrs = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        r = requests.get(channel_url, headers=hdrs, timeout=15)
        for pat in [r'"avatar":\{"thumbnails":\[\{"url":"([^"]+)"', r'"channelAvatarUrl":"([^"]+)"']:
            m = re.search(pat, r.text)
            if m:
                u = m.group(1)
                return ("https:" + u) if u.startswith("//") else u
    except Exception: pass
    return None

def download_full_low(url, out_dir):
    tmpl = os.path.join(out_dir, "full.%(ext)s")
    subprocess.run([sys.executable, "-m", "yt_dlp", "-f", "worst[ext=mp4]/worst",
                    "-o", tmpl, "--no-playlist", "-q", url], check=True, timeout=600)
    for f in os.listdir(out_dir):
        if f.startswith("full."): return os.path.join(out_dir, f)
    raise RuntimeError("Low-quality video download failed")

def download_clip_file(url, start, end, out_dir, idx):
    tmpl = os.path.join(out_dir, f"clip{idx}.%(ext)s")
    subprocess.run([sys.executable, "-m", "yt_dlp",
                    "--download-sections", f"*{secs_to_hms(start)}-{secs_to_hms(end)}",
                    "--force-keyframes-at-cuts",
                    "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
                    "-o", tmpl, "--no-playlist", "-q", url], check=True, timeout=300)
    for f in os.listdir(out_dir):
        if f.startswith(f"clip{idx}."): return os.path.join(out_dir, f)
    raise RuntimeError(f"Clip {idx} download failed")

def make_gif(video_path, duration):
    max_t = max(float(duration) - 1.5, 0.5)
    segs = []
    for _ in range(500):
        t = round(random.uniform(0, max_t), 3)
        if all(abs(t - s) >= 2.0 for s in segs): segs.append(t)
        if len(segs) == 5: break
    while len(segs) < 5: segs.append(round(random.uniform(0, max_t), 3))
    segs.sort()

    def build_fc(scale, fps):
        trims  = [f"[0:v]trim=start={t:.3f}:duration=1,setpts=PTS-STARTPTS[v{i}]" for i, t in enumerate(segs)]
        labels = "".join(f"[v{i}]" for i in range(5))
        return (";" .join(trims)
                + f";{labels}concat=n=5:v=1:a=0[cat]"
                + f";[cat]fps={fps},scale={scale}:-2:flags=lanczos,"
                  "boxblur=luma_radius=8:luma_power=1,"
                  "curves=all='0/0 1/0.38'[out]")

    with tempfile.TemporaryDirectory() as tmp:
        gif_path     = os.path.join(tmp, "out.gif")
        palette_path = os.path.join(tmp, "pal.png")
        for scale, fps in [(540, 10), (360, 8)]:
            fc = build_fc(scale, fps)
            try:
                run_ff(["-y", "-i", video_path,
                        "-filter_complex", fc + ";[out]palettegen=max_colors=128[pal]",
                        "-map", "[pal]", palette_path])
                run_ff(["-y", "-i", video_path, "-i", palette_path,
                        "-filter_complex", fc + ";[out][1:v]paletteuse=dither=bayer[final]",
                        "-map", "[final]", gif_path])
            except Exception:
                try: run_ff(["-y", "-i", video_path, "-filter_complex", fc, "-map", "[out]", gif_path])
                except Exception: continue
            data = open(gif_path, "rb").read()
            if len(data) <= 5 * 1024 * 1024: return data
        return open(gif_path, "rb").read()

def run_lesson_pipeline(url, info, avatar_url, category, clips, status):
    vid_title = info.get("title", "Untitled")
    thumb_url = info.get("thumbnail", "")
    duration  = float(info.get("duration") or 60)
    prop      = get_title_prop(LESSONS_DB)

    status("Creating main page\u2026", 0.10)
    main_body = {
        "parent": {"database_id": LESSONS_DB},
        "properties": {
            prop:   {"title":  [{"text": {"content": vid_title}}]},
            "Type": {"select": {"name": category}},
        },
    }
    if avatar_url:
        main_body["icon"] = {"type": "external", "external": {"url": avatar_url}}
    main    = n_post("/pages", main_body)
    main_id = main["id"]

    status("Adding thumbnail\u2026", 0.15)
    n_patch(f"/blocks/{main_id}/children", {"children": [
        {"object": "block", "type": "image",
         "image": {"type": "external", "external": {"url": thumb_url}}}
    ]})

    status("Creating Breakdown page\u2026", 0.20)
    breakdown_body = {
        "parent":     {"page_id": main_id},
        "properties": {"title": {"title": [{"text": {"content": "Breakdown"}}]}},
    }
    if avatar_url:
        breakdown_body["icon"] = {"type": "external", "external": {"url": avatar_url}}
    breakdown    = n_post("/pages", breakdown_body)
    breakdown_id = breakdown["id"]

    with tempfile.TemporaryDirectory() as tmp:
        status("Downloading video for GIF\u2026", 0.25)
        video_path = download_full_low(url, tmp)

        status("Generating GIF cover\u2026", 0.35)
        gif_data = make_gif(video_path, duration)

        status("Uploading GIF\u2026", 0.45)
        gif_url = upload_imgur_bytes(gif_data, "image/gif")

        status("Setting Breakdown cover\u2026", 0.50)
        n_patch(f"/pages/{breakdown_id}", {"cover": {"type": "external", "external": {"url": gif_url}}})

        status("Building Breakdown content\u2026", 0.55)
        n_patch(f"/blocks/{breakdown_id}/children", {"children": [
            {"object": "block", "type": "callout",
             "callout": {"rich_text": [], "icon": {"type": "emoji", "emoji": "\U0001f3ac"}, "color": "default",
                         "children": [{"object": "block", "type": "video",
                                       "video": {"type": "external", "external": {"url": url}}}]}}
        ]})

        status("Creating Clips database\u2026", 0.60)
        clips_db = n_post("/databases", {
            "parent":     {"page_id": breakdown_id},
            "is_inline":  True,
            "title":      [{"text": {"content": "Clips"}}],
            "properties": {"Name": {"title": {}}, "Link": {"url": {}}, "Notes": {"rich_text": {}}},
        })
        clips_db_id = clips_db["id"]
        time.sleep(0.6)

        for i, clip in enumerate(clips):
            n = i + 1
            status(f"Processing Clip {n} of {len(clips)}\u2026", 0.65 + i / len(clips) * 0.30)
            start, end, notes = clip["start"], clip["end"], clip["notes"]
            clip_name = clip["name"] if clip["name"] else f"Clip {n}"
            clip_path = download_clip_file(url, start, end, tmp, n)
            clip_url  = upload_imgur_video(clip_path)
            yt_ts     = f"https://www.youtube.com/watch?v={info.get('id','')}&t={start}s"
            page_body = {
                "parent": {"database_id": clips_db_id},
                "properties": {
                    "Name":  {"title":     [{"text": {"content": clip_name}}]},
                    "Link":  {"url":       yt_ts},
                    "Notes": {"rich_text": [{"text": {"content": notes}}] if notes else []},
                },
                "children": [{"object": "block", "type": "video",
                               "video": {"type": "external", "external": {"url": clip_url}}}],
            }
            if avatar_url:
                page_body["icon"] = {"type": "external", "external": {"url": avatar_url}}
            n_post("/pages", page_body)

    return vid_title

# ── Flask app ──────────────────────────────────────────────────────────────────

app   = Flask(__name__)
_jobs = {}

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MVS Studios · Hub</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg:     #0a0a0a;
    --bg2:    #111111;
    --bg3:    #181818;
    --bg4:    #1e1e1e;
    --bord:   #242424;
    --fg:     #ebebeb;
    --fg2:    #888888;
    --fg3:    #444444;
    --red:    #E03030;
    --green:  #2ecc71;
    --font:   'Helvetica Neue', Helvetica, Arial, sans-serif;
  }
  html, body { height: 100%; background: var(--bg); color: var(--fg); font-family: var(--font); }

  header {
    background: var(--bg2);
    border-bottom: 1px solid var(--bord);
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    position: sticky;
    top: 0;
    z-index: 10;
  }
  .logo { display: flex; align-items: center; gap: 10px; }
  .logo-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--red); }
  .logo-text { font-size: 12px; font-weight: 700; letter-spacing: .04em; color: var(--fg); }
  .logo-sub  { font-size: 10px; color: var(--fg3); margin-left: 2px; }

  nav {
    background: var(--bg2);
    border-bottom: 1px solid var(--bord);
    display: flex;
    padding: 0 24px;
    gap: 2px;
  }
  .tab {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--fg3);
    cursor: pointer;
    font-family: var(--font);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .05em;
    padding: 12px 16px 10px;
    transition: color .15s, border-color .15s;
    text-transform: uppercase;
  }
  .tab:hover { color: var(--fg2); }
  .tab.active { color: var(--fg); border-bottom-color: var(--red); }

  .panel { display: none; max-width: 560px; margin: 0 auto; padding: 28px 20px 60px; }
  .panel.active { display: block; }

  .drop-zone {
    border: 1.5px dashed var(--bord);
    border-radius: 8px;
    background: var(--bg3);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 220px;
    cursor: default;
    transition: border-color .15s, background .15s;
  }
  .drop-zone.hover  { border-color: var(--red); background: #1a0e0e; }
  .drop-zone.done   { border-color: var(--green); background: #0c1a0f; }
  .drop-zone.error  { border-color: #7a2020; background: #1a0c0c; }
  .drop-icon { margin-bottom: 12px; }
  .drop-label { font-size: 13px; color: var(--fg3); margin-bottom: 5px; }
  .drop-label.active-drag { color: var(--red); }
  .drop-ext { font-size: 10px; color: var(--fg3); opacity: .5; }
  .drop-result { text-align: center; }
  .drop-result .sym { font-size: 32px; font-weight: 700; margin-bottom: 8px; }
  .drop-result .sym.done  { color: var(--green); }
  .drop-result .sym.error { color: var(--red); }
  .drop-result .msg { font-size: 12px; color: var(--fg2); }

  .prog-wrap { width: 100%; padding: 0 30px; margin-top: 16px; display: none; }
  .prog-label { font-size: 11px; color: var(--fg2); margin-bottom: 6px; text-align: center; }
  .prog-track { height: 2px; background: var(--bg4); border-radius: 1px; overflow: hidden; }
  .prog-fill  { height: 2px; background: var(--red); border-radius: 1px; width: 0%; transition: width .3s; }

  label { display: block; font-size: 10px; color: var(--fg2); margin-bottom: 4px; text-transform: uppercase; letter-spacing: .04em; }
  input[type=text], input[type=url], textarea {
    width: 100%;
    background: var(--bg3);
    border: 1px solid var(--bord);
    border-radius: 4px;
    color: var(--fg);
    font-family: var(--font);
    font-size: 12px;
    padding: 9px 10px;
    outline: none;
    transition: border-color .15s;
  }
  input:focus, textarea:focus { border-color: #383838; }
  textarea { resize: vertical; min-height: 56px; }
  .field-group { margin-bottom: 14px; }

  .cat-row { display: flex; gap: 6px; flex-wrap: wrap; }
  .cat-btn {
    background: var(--bg3);
    border: 1px solid var(--bord);
    border-radius: 4px;
    color: var(--fg3);
    cursor: pointer;
    font-family: var(--font);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: .04em;
    padding: 7px 14px;
    text-transform: uppercase;
    transition: background .15s, color .15s, border-color .15s;
  }
  .cat-btn.active { background: var(--red); border-color: var(--red); color: #fff; }

  .divider { border: none; border-top: 1px solid var(--bord); margin: 20px 0; }
  .section-label { font-size: 10px; font-weight: 700; color: var(--fg2); letter-spacing: .06em; text-transform: uppercase; margin-bottom: 12px; }

  .clip-card {
    background: var(--bg3);
    border: 1px solid var(--bord);
    border-radius: 6px;
    padding: 14px;
    margin-bottom: 8px;
  }
  .clip-header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
  .clip-num { font-size: 10px; font-weight: 700; color: var(--fg3); white-space: nowrap; text-transform: uppercase; letter-spacing: .05em; }
  .clip-name-wrap { flex: 1; }
  .ts-row { display: flex; gap: 8px; margin-bottom: 8px; }
  .ts-row .field { flex: 1; display: flex; flex-direction: column; }
  .ts-hint { font-size: 9px; color: var(--fg3); margin-top: 3px; }

  #add-clip {
    background: var(--bg3);
    border: 1px dashed var(--bord);
    border-radius: 4px;
    color: var(--fg3);
    cursor: pointer;
    font-family: var(--font);
    font-size: 11px;
    padding: 9px;
    width: 100%;
    text-align: center;
    transition: border-color .15s, color .15s;
  }
  #add-clip:hover { border-color: #383838; color: var(--fg2); }

  .submit-btn {
    background: var(--red);
    border: none;
    border-radius: 4px;
    color: #fff;
    cursor: pointer;
    font-family: var(--font);
    font-size: 12px;
    font-weight: 700;
    padding: 10px 22px;
    float: right;
    transition: background .15s;
    letter-spacing: .02em;
  }
  .submit-btn:disabled { background: var(--bg4); color: var(--fg3); cursor: not-allowed; }
  .submit-btn.done { background: var(--green); }

  #lesson-status { font-size: 11px; color: var(--fg2); min-height: 16px; margin-bottom: 6px; }
  #lesson-prog-wrap { background: var(--bg4); border-radius: 1px; height: 2px; margin-bottom: 14px; overflow: hidden; }
  #lesson-prog-fill { height: 2px; width: 0%; background: var(--red); transition: width .3s; }
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-dot"></div>
    <span class="logo-text">MVS Studios</span>
    <span class="logo-sub">Hub</span>
  </div>
</header>

<nav>
  <button class="tab active" data-panel="frame">Frame</button>
  <button class="tab" data-panel="clip">Clip</button>
  <button class="tab" data-panel="lesson">Lesson</button>
</nav>

<div class="panel active" id="panel-frame">
  <div class="drop-zone" id="frame-drop">
    <svg class="drop-icon" width="24" height="32" viewBox="0 0 24 32" fill="none">
      <line x1="12" y1="0" x2="12" y2="20" stroke="#444" stroke-width="2" stroke-linecap="round"/>
      <polyline points="4,12 12,20 20,12" stroke="#444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <line x1="2" y1="28" x2="22" y2="28" stroke="#444" stroke-width="2" stroke-linecap="round"/>
    </svg>
    <div class="drop-label" id="frame-label">Drop image here</div>
    <div class="drop-ext">JPG · PNG · WEBP</div>
    <div class="prog-wrap" id="frame-prog">
      <div class="prog-label" id="frame-prog-label"></div>
      <div class="prog-track"><div class="prog-fill" id="frame-prog-fill"></div></div>
    </div>
  </div>
</div>

<div class="panel" id="panel-clip">
  <div class="drop-zone" id="clip-drop">
    <svg class="drop-icon" width="24" height="32" viewBox="0 0 24 32" fill="none">
      <line x1="12" y1="0" x2="12" y2="20" stroke="#444" stroke-width="2" stroke-linecap="round"/>
      <polyline points="4,12 12,20 20,12" stroke="#444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <line x1="2" y1="28" x2="22" y2="28" stroke="#444" stroke-width="2" stroke-linecap="round"/>
    </svg>
    <div class="drop-label" id="clip-label">Drop video here</div>
    <div class="drop-ext">MP4 · MOV · MKV · AVI · M4V · WEBM</div>
    <div class="prog-wrap" id="clip-prog">
      <div class="prog-label" id="clip-prog-label"></div>
      <div class="prog-track"><div class="prog-fill" id="clip-prog-fill"></div></div>
    </div>
  </div>
</div>

<div class="panel" id="panel-lesson">
  <div class="field-group">
    <label for="yt-url">YouTube URL</label>
    <input type="url" id="yt-url" placeholder="https://www.youtube.com/watch?v=...">
  </div>
  <div class="field-group">
    <label>Type</label>
    <div class="cat-row" id="cat-row">
      <button class="cat-btn" data-cat="Business">Business</button>
      <button class="cat-btn" data-cat="Technical">Technical</button>
      <button class="cat-btn" data-cat="Storytelling">Storytelling</button>
    </div>
  </div>
  <hr class="divider">
  <div class="section-label">Clips</div>
  <div id="clips-container"></div>
  <button id="add-clip">+ Add clip</button>
  <hr class="divider">
  <div id="lesson-status"></div>
  <div id="lesson-prog-wrap"><div id="lesson-prog-fill"></div></div>
  <button class="submit-btn" id="submit-btn">Push to Notion →</button>
  <div style="clear:both"></div>
</div>

<script>
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('panel-' + tab.dataset.panel).classList.add('active');
  });
});

function makeDropZone(zoneId, labelId, progId, progLabelId, progFillId, acceptExts, uploadRoute) {
  const zone      = document.getElementById(zoneId);
  const label     = document.getElementById(labelId);
  const prog      = document.getElementById(progId);
  const progLabel = document.getElementById(progLabelId);
  const progFill  = document.getElementById(progFillId);
  const defaultLabel = label.textContent;
  let busy = false;

  function setProgress(msg, pct) {
    prog.style.display = 'block';
    progLabel.textContent = msg;
    progFill.style.width = (pct * 100) + '%';
  }

  function setResult(state, msg) {
    zone.className = 'drop-zone ' + state;
    prog.style.display = 'none';
    zone.querySelector('.drop-icon').style.display = 'none';
    zone.querySelector('.drop-ext').style.display = 'none';
    label.style.display = 'none';
    const existing = zone.querySelector('.drop-result');
    if (existing) existing.remove();
    const div = document.createElement('div');
    div.className = 'drop-result';
    div.innerHTML = '<div class="sym ' + state + '">' + (state === 'done' ? '\u2713' : '\u2715') + '</div><div class="msg">' + msg + '</div>';
    zone.appendChild(div);
    if (state === 'done') setTimeout(reset, 3000);
  }

  function reset() {
    zone.className = 'drop-zone';
    zone.querySelector('.drop-icon').style.display = '';
    zone.querySelector('.drop-ext').style.display = '';
    label.style.display = '';
    label.textContent = defaultLabel;
    label.className = 'drop-label';
    prog.style.display = 'none';
    progFill.style.width = '0%';
    const r = zone.querySelector('.drop-result');
    if (r) r.remove();
    busy = false;
  }

  zone.addEventListener('dragover', e => {
    e.preventDefault();
    if (!busy) { zone.classList.add('hover'); label.className = 'drop-label active-drag'; label.textContent = 'Release to add'; }
  });
  zone.addEventListener('dragleave', () => {
    if (!busy) { zone.classList.remove('hover'); label.className = 'drop-label'; label.textContent = defaultLabel; }
  });
  zone.addEventListener('drop', async e => {
    e.preventDefault();
    if (busy) return;
    zone.classList.remove('hover');
    label.className = 'drop-label';
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const ext = file.name.split('.').pop().toLowerCase();
    if (!acceptExts.includes(ext)) { setResult('error', 'Unsupported: .' + ext); return; }
    busy = true;
    setProgress('Uploading\u2026', 0.1);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch(uploadRoute, { method: 'POST', body: fd });
      const j   = await res.json();
      if (j.ok) setResult('done', '\u2713  ' + j.label + ' added to Notion!');
      else setResult('error', j.error || 'Unknown error');
    } catch(err) { setResult('error', err.message); busy = false; }
  });
}

makeDropZone('frame-drop','frame-label','frame-prog','frame-prog-label','frame-prog-fill',
             ['jpg','jpeg','png','webp'], '/upload/frame');
makeDropZone('clip-drop','clip-label','clip-prog','clip-prog-label','clip-prog-fill',
             ['mp4','mov','avi','mkv','m4v','webm','mxf','wmv'], '/upload/clip');

let selectedCat = '';
document.querySelectorAll('.cat-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    selectedCat = btn.dataset.cat;
    document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  });
});

let clipCount = 0;
function addClip() {
  clipCount++;
  const idx  = clipCount;
  const card = document.createElement('div');
  card.className  = 'clip-card';
  card.dataset.idx = idx;
  card.innerHTML = `
    <div class="clip-header">
      <span class="clip-num">Clip ${idx}</span>
      <div class="clip-name-wrap"><label>Name</label><input type="text" class="clip-name-input" placeholder="optional"></div>
    </div>
    <div class="ts-row">
      <div class="field"><label>Start</label><input type="text" class="clip-start" placeholder="mm:ss"><span class="ts-hint">ss · mm:ss · hh:mm:ss</span></div>
      <div class="field"><label>End</label><input type="text" class="clip-end" placeholder="mm:ss"></div>
    </div>
    <label>Notes</label>
    <textarea class="clip-notes" placeholder="optional"></textarea>
  `;
  let triggered = false;
  function checkAuto() {
    if (triggered) return;
    if (card.querySelector('.clip-start').value.trim() && card.querySelector('.clip-end').value.trim()) {
      triggered = true; addClip();
    }
  }
  card.querySelector('.clip-start').addEventListener('input', checkAuto);
  card.querySelector('.clip-end').addEventListener('input', checkAuto);
  document.getElementById('clips-container').appendChild(card);
  card.querySelector('.clip-name-input').focus();
}
document.getElementById('add-clip').addEventListener('click', addClip);
addClip();

function setLessonStatus(msg, pct) {
  document.getElementById('lesson-status').textContent = msg;
  if (pct !== undefined) document.getElementById('lesson-prog-fill').style.width = (pct * 100) + '%';
}

document.getElementById('submit-btn').addEventListener('click', async () => {
  const url = document.getElementById('yt-url').value.trim();
  if (!url) { setLessonStatus('\u26a0  Enter a YouTube URL'); return; }
  if (!selectedCat) { setLessonStatus('\u26a0  Select a type'); return; }
  const clips = [];
  let valid = true;
  document.querySelectorAll('.clip-card').forEach(card => {
    const s = card.querySelector('.clip-start').value.trim();
    const e = card.querySelector('.clip-end').value.trim();
    if (!s && !e) return;
    if (!s || !e) { setLessonStatus('\u26a0  Clip ' + card.dataset.idx + ': fill both timestamps'); valid = false; return; }
    clips.push({ start: s, end: e, notes: card.querySelector('.clip-notes').value.trim(), name: card.querySelector('.clip-name-input').value.trim() });
  });
  if (!valid) return;
  if (!clips.length) { setLessonStatus('\u26a0  Add at least one clip with timestamps'); return; }
  const btn = document.getElementById('submit-btn');
  btn.disabled = true; btn.textContent = 'Working\u2026';
  setLessonStatus('Starting\u2026', 0.02);
  const res = await fetch('/upload/lesson', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({url, category: selectedCat, clips}) });
  const {job_id} = await res.json();
  const es = new EventSource('/progress/' + job_id);
  es.onmessage = ev => {
    const d = JSON.parse(ev.data);
    if (d.type === 'progress') { setLessonStatus(d.msg, d.pct); }
    else if (d.type === 'done') { setLessonStatus('\u2713  Added "' + d.title + '" to Notion!', 1.0); btn.textContent = '\u2713 Done'; btn.classList.add('done'); es.close(); }
    else if (d.type === 'error') { setLessonStatus('\u2715  ' + d.msg, 0); btn.disabled = false; btn.textContent = 'Push to Notion \u2192'; btn.classList.remove('done'); es.close(); }
  };
});
</script>
</body>
</html>"""


@app.route("/")
def index():
    return HTML


@app.route("/upload/frame", methods=["POST"])
def upload_frame():
    try:
        f = request.files.get("file")
        if not f: return jsonify(ok=False, error="No file")
        label = handle_frame(f.read())
        return jsonify(ok=True, label=label)
    except Exception as e:
        return jsonify(ok=False, error=str(e)[:120])


@app.route("/upload/clip", methods=["POST"])
def upload_clip():
    try:
        f = request.files.get("file")
        if not f: return jsonify(ok=False, error="No file")
        label = handle_clip(f.read(), f.filename or "clip.mp4")
        return jsonify(ok=True, label=label)
    except Exception as e:
        return jsonify(ok=False, error=str(e)[:120])


@app.route("/upload/lesson", methods=["POST"])
def upload_lesson():
    data     = request.get_json(force=True)
    url      = data["url"]
    category = data["category"]
    clips    = []
    for i, c in enumerate(data["clips"], 1):
        s = parse_ts(c["start"])
        e = parse_ts(c["end"])
        if e <= s:
            return jsonify(error=f"Clip {i}: end must be after start"), 400
        clips.append({"start": s, "end": e, "notes": c.get("notes", ""), "name": c.get("name", "")})
    job_id = str(uuid.uuid4())
    _jobs[job_id] = []

    def worker():
        q = _jobs[job_id]
        def status(msg, pct=None):
            q.append(json.dumps({"type": "progress", "msg": msg, "pct": pct or 0}))
        try:
            status("Fetching video info\u2026", 0.04)
            info = get_video_info(url)
            status("Fetching channel avatar\u2026", 0.08)
            ch_url = info.get("channel_url") or info.get("uploader_url", "")
            avatar = get_channel_avatar(ch_url) if ch_url else None
            title  = run_lesson_pipeline(url, info, avatar, category, clips, status)
            q.append(json.dumps({"type": "done", "title": title}))
        except Exception as e:
            q.append(json.dumps({"type": "error", "msg": str(e)[:200]}))

    threading.Thread(target=worker, daemon=True).start()
    return jsonify(job_id=job_id)


@app.route("/progress/<job_id>")
def progress(job_id):
    def stream():
        sent = 0
        while True:
            q = _jobs.get(job_id, [])
            while sent < len(q):
                yield f"data: {q[sent]}\n\n"
                sent += 1
                msg = json.loads(q[sent - 1])
                if msg["type"] in ("done", "error"):
                    _jobs.pop(job_id, None)
                    return
            time.sleep(0.5)
    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    import webbrowser
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  MVS Studios Hub → http://localhost:{port}\n")
    # Open browser automatically after a short delay
    threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    app.run(host="127.0.0.1", port=port, threaded=True)
