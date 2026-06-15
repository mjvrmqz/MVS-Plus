#!/usr/bin/env python3
"""
MSV Studios · Clips Builder  (Flask web version)
Paste a YouTube link → pick type → define clips with timestamps & notes
→ pushes everything to Notion with full Breakdown sub-page.
"""

import subprocess, sys, os, io, threading, requests, json, re
import random, tempfile, base64, glob, time
import os
from pathlib import Path
from flask import Flask, request, jsonify, Response

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

# ── constants ──────────────────────────────────────────────────────────────────
NOTION_KEY = os.environ.get("NOTION_KEY", "")
LESSONS_DB_ID  = os.environ.get("LESSONS_DB_ID", "")
NOTION_HDR   = {
    "Authorization":  f"Bearer {NOTION_KEY}",
    "Content-Type":   "application/json",
    "Notion-Version": "2022-06-28",
}
IMGUR_CLIENT = "546c25a59c58ad7"

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

def get_video_info(url):
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        return ydl.extract_info(url, download=False)

def get_channel_avatar(channel_url):
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
    max_t = max(float(duration) - 1.5, 0.5)
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
                run_ff(["-y", "-i", video_path,
                        "-filter_complex", fc + ";[out]palettegen=max_colors=128[pal]",
                        "-map", "[pal]", palette_path])
                run_ff(["-y", "-i", video_path, "-i", palette_path,
                        "-filter_complex", fc + ";[out][1:v]paletteuse=dither=bayer[final]",
                        "-map", "[final]", gif_path])
            except Exception:
                try:
                    run_ff(["-y", "-i", video_path,
                            "-filter_complex", fc, "-map", "[out]", gif_path])
                except Exception:
                    continue

            data = open(gif_path, "rb").read()
            if len(data) <= 5 * 1024 * 1024:
                return data

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

    status("Creating main page…", 0.10)
    main_body = {
        "parent": {"database_id": LESSONS_DB_ID},
        "properties": {
            prop:   {"title":  [{"text": {"content": vid_title}}]},
            "Type": {"select": {"name": category}},
        },
    }
    if avatar_url:
        main_body["icon"] = {"type": "external", "external": {"url": avatar_url}}
    main    = n_post("/pages", main_body)
    main_id = main["id"]

    status("Adding thumbnail…", 0.15)
    n_patch(f"/blocks/{main_id}/children", {"children": [
        {"object": "block", "type": "image",
         "image": {"type": "external", "external": {"url": thumb_url}}}
    ]})

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
        status("Downloading video for GIF…", 0.25)
        video_path = download_full_low(url, tmp)

        status("Generating GIF cover…", 0.35)
        gif_data = make_gif(video_path, duration)

        status("Uploading GIF…", 0.45)
        gif_url = upload_imgur_bytes(gif_data)

        status("Setting Breakdown cover…", 0.50)
        n_patch(f"/pages/{breakdown_id}", {
            "cover": {"type": "external", "external": {"url": gif_url}}
        })

        status("Building Breakdown content…", 0.55)
        n_patch(f"/blocks/{breakdown_id}/children", {"children": [
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
        time.sleep(0.6)

        for i, clip in enumerate(clips):
            n = i + 1
            status(f"Processing Clip {n} of {len(clips)}…",
                   0.65 + i / len(clips) * 0.30)

            start, end, notes = clip["start"], clip["end"], clip["notes"]
            clip_name = clip["name"] if clip["name"] else f"Clip {n}"

            clip_path = download_clip_file(url, start, end, tmp, n)
            clip_url  = upload_imgur_video(clip_path)
            yt_ts     = f"https://www.youtube.com/watch?v={vid_id}&t={start}s"

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

# ── Flask app ──────────────────────────────────────────────────────────────────

app = Flask(__name__)

# SSE event queues keyed by job_id
_jobs = {}

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MSV Studios · Clips Builder</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg:     #0e0e0e;
    --bg2:    #161616;
    --bg3:    #1c1c1c;
    --bord:   #2c2c2c;
    --fg:     #e8e8e8;
    --fg2:    #999999;
    --fg3:    #555555;
    --accent: #ff0033;
    --green:  #37c337;
    --font:   'Helvetica Neue', Helvetica, Arial, sans-serif;
  }
  html, body { height: 100%; background: var(--bg); color: var(--fg); font-family: var(--font); }

  /* header */
  header {
    background: #0a0a0a;
    height: 46px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    position: sticky;
    top: 0;
    z-index: 10;
  }
  header .title { font-size: 13px; font-weight: 700; }
  header .sub   { font-size: 10px; color: var(--fg3); }

  /* layout */
  main { max-width: 580px; margin: 0 auto; padding: 22px 18px 40px; }

  label { display: block; font-size: 11px; color: var(--fg2); margin-bottom: 5px; }

  input[type=text], input[type=url], textarea {
    width: 100%;
    background: var(--bg2);
    border: 1px solid var(--bord);
    border-radius: 4px;
    color: var(--fg);
    font-family: var(--font);
    font-size: 12px;
    padding: 9px 10px;
    outline: none;
    transition: border-color .15s;
  }
  input:focus, textarea:focus { border-color: #444; }
  textarea { resize: vertical; min-height: 64px; }

  .section-title {
    font-size: 12px;
    font-weight: 700;
    color: var(--fg);
    margin: 20px 0 10px;
  }
  hr { border: none; border-top: 1px solid var(--bord); margin: 18px 0; }

  /* category buttons */
  .cat-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
  .cat-btn {
    background: var(--bg3);
    border: 1px solid var(--bord);
    border-radius: 4px;
    color: var(--fg2);
    cursor: pointer;
    font-family: var(--font);
    font-size: 11px;
    padding: 7px 14px;
    transition: background .15s, color .15s;
  }
  .cat-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }

  /* clip card */
  .clip-card {
    background: var(--bg3);
    border: 1px solid var(--bord);
    border-radius: 6px;
    padding: 14px 14px 10px;
    margin-bottom: 10px;
  }
  .clip-header {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 10px;
  }
  .clip-num { font-size: 11px; font-weight: 700; color: var(--fg); white-space: nowrap; }
  .clip-name { flex: 1; }
  .ts-row { display: flex; gap: 10px; margin-bottom: 8px; }
  .ts-row .field { display: flex; flex-direction: column; flex: 1; }
  .ts-hint { font-size: 9px; color: var(--fg3); margin-top: 3px; }

  #add-clip {
    background: var(--bg2);
    border: 1px dashed var(--bord);
    border-radius: 4px;
    color: var(--fg3);
    cursor: pointer;
    font-family: var(--font);
    font-size: 11px;
    padding: 8px;
    width: 100%;
    text-align: center;
    transition: border-color .15s, color .15s;
  }
  #add-clip:hover { border-color: #444; color: var(--fg2); }

  /* progress */
  #status-msg { font-size: 11px; color: var(--fg2); min-height: 16px; margin-bottom: 6px; }
  #progress-bar-wrap {
    background: var(--bg3);
    border-radius: 2px;
    height: 3px;
    margin-bottom: 12px;
    overflow: hidden;
  }
  #progress-bar {
    height: 3px;
    width: 0%;
    background: var(--accent);
    transition: width .3s;
  }

  /* submit */
  #submit-btn {
    background: var(--accent);
    border: none;
    border-radius: 4px;
    color: #fff;
    cursor: pointer;
    font-family: var(--font);
    font-size: 12px;
    font-weight: 700;
    padding: 10px 20px;
    float: right;
    transition: background .15s;
  }
  #submit-btn:disabled { background: #2a2a2a; color: var(--fg3); cursor: not-allowed; }
  #submit-btn.done { background: var(--green); }
</style>
</head>
<body>
<header>
  <span class="title">Clips Builder</span>
  <span class="sub">MSV Studios</span>
</header>
<main>
  <!-- URL -->
  <label for="yt-url">YouTube URL</label>
  <input type="url" id="yt-url" placeholder="https://www.youtube.com/watch?v=...">

  <!-- Type -->
  <p class="section-title" style="margin-top:18px">Type</p>
  <div class="cat-row" id="cat-row">
    <button class="cat-btn" data-cat="Business">Business</button>
    <button class="cat-btn" data-cat="Technical">Technical</button>
    <button class="cat-btn" data-cat="Storytelling">Storytelling</button>
  </div>

  <hr>

  <!-- Clips -->
  <p class="section-title">Clips</p>
  <div id="clips-container"></div>
  <button id="add-clip">+ Add clip</button>

  <hr>

  <!-- Status -->
  <div id="status-msg"></div>
  <div id="progress-bar-wrap"><div id="progress-bar"></div></div>

  <!-- Submit -->
  <button id="submit-btn">Push to Notion &rarr;</button>
  <div style="clear:both"></div>
</main>

<script>
  // ── category selection ────────────────────────────────────────────────
  let selectedCat = '';
  document.querySelectorAll('.cat-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      selectedCat = btn.dataset.cat;
      document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });

  // ── clip rows ─────────────────────────────────────────────────────────
  let clipCount = 0;

  function addClip() {
    clipCount++;
    const idx = clipCount;
    const card = document.createElement('div');
    card.className = 'clip-card';
    card.dataset.idx = idx;
    card.innerHTML = `
      <div class="clip-header">
        <span class="clip-num">Clip ${idx}</span>
        <div class="clip-name">
          <label>Name</label>
          <input type="text" class="clip-name-input" placeholder="optional">
        </div>
      </div>
      <div class="ts-row">
        <div class="field">
          <label>Start</label>
          <input type="text" class="clip-start" placeholder="mm:ss">
          <span class="ts-hint">ss or mm:ss or hh:mm:ss</span>
        </div>
        <div class="field">
          <label>End</label>
          <input type="text" class="clip-end" placeholder="mm:ss">
          <span class="ts-hint"></span>
        </div>
      </div>
      <label>Notes</label>
      <textarea class="clip-notes" placeholder="optional"></textarea>
    `;
    // auto-add next clip when both timestamps filled
    let triggered = false;
    function checkAutoAdd() {
      if (triggered) return;
      const s = card.querySelector('.clip-start').value.trim();
      const e = card.querySelector('.clip-end').value.trim();
      if (s && e) { triggered = true; addClip(); }
    }
    card.querySelector('.clip-start').addEventListener('input', checkAutoAdd);
    card.querySelector('.clip-end').addEventListener('input', checkAutoAdd);
    document.getElementById('clips-container').appendChild(card);
    card.querySelector('.clip-name-input').focus();
  }

  document.getElementById('add-clip').addEventListener('click', addClip);
  addClip(); // seed Clip 1

  // ── status helpers ────────────────────────────────────────────────────
  function setStatus(msg, pct) {
    document.getElementById('status-msg').textContent = msg;
    if (pct !== undefined)
      document.getElementById('progress-bar').style.width = (pct * 100) + '%';
  }

  // ── submit ────────────────────────────────────────────────────────────
  document.getElementById('submit-btn').addEventListener('click', async () => {
    const url = document.getElementById('yt-url').value.trim();
    if (!url) { setStatus('⚠  Enter a YouTube URL'); return; }
    if (!selectedCat) { setStatus('⚠  Select a type'); return; }

    const clips = [];
    let valid = true;
    document.querySelectorAll('.clip-card').forEach(card => {
      const s = card.querySelector('.clip-start').value.trim();
      const e = card.querySelector('.clip-end').value.trim();
      if (!s && !e) return;
      if (!s || !e) { setStatus(`⚠  Clip ${card.dataset.idx}: fill in both timestamps`); valid = false; return; }
      clips.push({
        start: s,
        end:   e,
        notes: card.querySelector('.clip-notes').value.trim(),
        name:  card.querySelector('.clip-name-input').value.trim(),
      });
    });
    if (!valid) return;
    if (!clips.length) { setStatus('⚠  Add at least one clip with timestamps'); return; }

    const btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.textContent = 'Working…';
    setStatus('Starting…', 0.02);

    const res = await fetch('/submit', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url, category: selectedCat, clips}),
    });
    const {job_id} = await res.json();

    // Stream SSE progress
    const es = new EventSource(`/progress/${job_id}`);
    es.onmessage = ev => {
      const d = JSON.parse(ev.data);
      if (d.type === 'progress') {
        setStatus(d.msg, d.pct);
      } else if (d.type === 'done') {
        setStatus(`✓  Added "${d.title}" to Notion!`, 1.0);
        btn.textContent = '✓ Done';
        btn.classList.add('done');
        es.close();
      } else if (d.type === 'error') {
        setStatus(`✗  ${d.msg}`, 0);
        btn.disabled = false;
        btn.textContent = 'Push to Notion →';
        btn.classList.remove('done');
        es.close();
      }
    };
  });
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return HTML

@app.route("/submit", methods=["POST"])
def submit():
    data     = request.get_json(force=True)
    url      = data["url"]
    category = data["category"]
    raw_clips= data["clips"]

    # Validate & parse clips
    clips = []
    for i, c in enumerate(raw_clips, 1):
        s = parse_ts(c["start"])
        e = parse_ts(c["end"])
        if e <= s:
            return jsonify({"error": f"Clip {i}: end must be after start"}), 400
        clips.append({"start": s, "end": e, "notes": c.get("notes", ""), "name": c.get("name", "")})

    import uuid
    job_id = str(uuid.uuid4())
    _jobs[job_id] = []

    def worker():
        q = _jobs[job_id]
        def status(msg, pct=None):
            q.append(json.dumps({"type": "progress", "msg": msg, "pct": pct or 0}))

        try:
            status("Fetching video info…", 0.04)
            info = get_video_info(url)

            status("Fetching channel avatar…", 0.08)
            ch_url = info.get("channel_url") or info.get("uploader_url", "")
            avatar = get_channel_avatar(ch_url) if ch_url else None

            title = run_pipeline(url, info, avatar, category, clips, status)
            q.append(json.dumps({"type": "done", "title": title}))
        except Exception as e:
            q.append(json.dumps({"type": "error", "msg": str(e)[:200]}))

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"job_id": job_id})

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
    app.run(host="0.0.0.0", port=5000, threaded=True)
