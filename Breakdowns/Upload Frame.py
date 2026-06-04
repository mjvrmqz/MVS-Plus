#!/usr/bin/env python3
import io, os, base64, requests
from pathlib import Path
from flask import Flask, request, jsonify
from PIL import Image, ImageFilter, ImageEnhance

NOTION_KEY = os.environ.get("NOTION_KEY", "")
INSPIRATION_DB_ID  = os.environ.get("INSPIRATION_DB_ID", "")
NOTION_HDR   = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

app = Flask(__name__)

def upload_bytes(data, mime):
    b64 = base64.b64encode(data).decode()
    r = requests.post(
        "https://api.imgur.com/3/image",
        headers={"Authorization": "Client-ID 546c25a59c58ad7"},
        data={"image": b64, "type": "base64"},
        timeout=60,
    )
    r.raise_for_status()
    j = r.json()
    if j.get("success"): return j["data"]["link"]
    raise RuntimeError(f"imgur upload failed: {j.get('data', {}).get('error', j)}")

def make_cover(img_bytes):
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

def get_next_inspiration_number():
    payload = {"filter": {"property": "title", "title": {"starts_with": "Inspiration "}}}
    r = requests.post(f"https://api.notion.com/v1/databases/{INSPIRATION_DB_ID}/query",
                      headers=NOTION_HDR, json=payload)
    if r.status_code != 200: return 1
    pages = r.json().get("results", [])
    nums = []
    for p in pages:
        for prop in p.get("properties", {}).values():
            if prop.get("type") == "title":
                for t in prop.get("title", []):
                    name = t.get("plain_text", "")
                    if name.startswith("Inspiration "):
                        try: nums.append(int(name.split(" ", 1)[1]))
                        except ValueError: pass
    return max(nums) + 1 if nums else 1

def push_to_notion(orig_url, cover_url, label):
    r = requests.get(f"https://api.notion.com/v1/databases/{INSPIRATION_DB_ID}", headers=NOTION_HDR)
    title_prop = "Name"
    if r.status_code == 200:
        for k, v in r.json().get("properties", {}).items():
            if v.get("type") == "title": title_prop = k; break
    payload = {
        "parent":  {"database_id": INSPIRATION_DB_ID},
        "cover":   {"type": "external", "external": {"url": cover_url}},
        "properties": {title_prop: {"title": [{"text": {"content": label}}]}},
        "children": [{"object": "block", "type": "image", "image": {"type": "external", "external": {"url": orig_url}}}],
    }
    return requests.post("https://api.notion.com/v1/pages", headers=NOTION_HDR, json=payload)

@app.route("/")
def index():
    return """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>MVS Studios · Inspiration Drop</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #0e0e0e; font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; }
    header { position: fixed; top: 0; left: 0; right: 0; background: #0a0a0a; padding: 14px 18px; display: flex; justify-content: space-between; align-items: center; }
    header h1 { color: #ebebeb; font-size: 13px; font-weight: 600; }
    header span { color: #464646; font-size: 10px; }
    #drop { width: 440px; height: 290px; border: 1.5px dashed #2c2c2c; border-radius: 10px; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: default; transition: border-color 0.15s, background 0.15s; background: #161616; }
    #drop.hover { border-color: #376437; background: #121f12; }
    #drop.done { border-color: #376437; background: #0c1a0c; }
    #drop.error { border-color: #7a2020; background: #1a0c0c; }
    .arrow { width: 24px; height: 36px; margin-bottom: 12px; }
    .label { color: #464646; font-size: 14px; margin-bottom: 6px; }
    .label.hover { color: #4ba04b; }
    .exts { color: #282828; font-size: 10px; }
    .status { color: #a0a0a0; font-size: 13px; text-align: center; padding: 0 20px; }
    .symbol { font-size: 36px; font-weight: 700; margin-bottom: 8px; }
    .symbol.done { color: #37be37; }
    .symbol.error { color: #be3737; }
    #bar-track { width: 360px; height: 3px; background: #262626; border-radius: 2px; margin-top: 14px; overflow: hidden; }
    #bar-fill { height: 100%; background: #ff0033; border-radius: 2px; width: 0%; transition: width 0.2s; }
  </style>
</head>
<body>
  <header><h1>Inspiration Drop</h1><span>MVS Studios</span></header>
  <div id="drop">
    <svg class="arrow" viewBox="0 0 24 36" fill="none" stroke="#2c2c2c" stroke-width="2" stroke-linecap="round">
      <line x1="12" y1="0" x2="12" y2="24"/><polyline points="4,14 12,24 20,14"/>
      <line x1="2" y1="32" x2="22" y2="32"/>
    </svg>
    <div class="label" id="lbl">Drop image here</div>
    <div class="exts">JPG · PNG · WEBP</div>
    <div id="bar-track" style="display:none"><div id="bar-fill"></div></div>
    <div class="status" id="status" style="display:none"></div>
  </div>
  <script>
    const drop = document.getElementById('drop');
    const lbl = document.getElementById('lbl');
    const statusEl = document.getElementById('status');
    const barTrack = document.getElementById('bar-track');
    const barFill = document.getElementById('bar-fill');
    const arrow = drop.querySelector('.arrow');
    const exts = drop.querySelector('.exts');

    function setWorking(msg, pct) {
      drop.className = '';
      arrow.style.display = 'none';
      lbl.style.display = 'none';
      exts.style.display = 'none';
      barTrack.style.display = 'block';
      statusEl.style.display = 'block';
      statusEl.textContent = msg;
      barFill.style.width = (pct * 100) + '%';
    }

    function setResult(state, msg) {
      drop.className = state;
      arrow.style.display = 'none';
      lbl.style.display = 'none';
      exts.style.display = 'none';
      barTrack.style.display = 'none';
      statusEl.style.display = 'block';
      drop.insertAdjacentHTML('afterbegin', '<div class="symbol ' + state + '" id="sym">' + (state === 'done' ? '\u2713' : '\u2715') + '</div>');
      statusEl.textContent = msg;
      if (state === 'done') setTimeout(reset, 3000);
    }

    function reset() {
      drop.className = '';
      document.getElementById('sym') && document.getElementById('sym').remove();
      arrow.style.display = '';
      lbl.style.display = '';
      lbl.className = 'label';
      exts.style.display = '';
      barTrack.style.display = 'none';
      statusEl.style.display = 'none';
      barFill.style.width = '0%';
    }

    drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('hover'); lbl.className = 'label hover'; lbl.textContent = 'Release to add'; arrow.style.stroke = '#376437'; });
    drop.addEventListener('dragleave', () => { drop.classList.remove('hover'); lbl.className = 'label'; lbl.textContent = 'Drop image here'; arrow.style.stroke = '#2c2c2c'; });
    drop.addEventListener('drop', async e => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (!file) return;
      const ext = file.name.split('.').pop().toLowerCase();
      if (!['jpg','jpeg','png','webp'].includes(ext)) { setResult('error', 'Unsupported: .' + ext); return; }
      setWorking('Uploading image\u2026', 0.15);
      const fd = new FormData();
      fd.append('file', file);
      try {
        const res = await fetch('/upload', { method: 'POST', body: fd });
        const j = await res.json();
        if (j.ok) setResult('done', '\u2713  Added to Notion!');
        else setResult('error', j.error || 'Unknown error');
      } catch(err) { setResult('error', err.message); }
    });
  </script>
</body>
</html>"""

@app.route("/upload", methods=["POST"])
def upload():
    try:
        f = request.files.get("file")
        if not f: return jsonify(ok=False, error="No file")
        img_bytes = f.read()
        orig_url = upload_bytes(img_bytes, f.mimetype or "image/jpeg")
        cover_bytes = make_cover(img_bytes)
        cover_url = upload_bytes(cover_bytes, "image/jpeg")
        label = f"Inspiration {get_next_inspiration_number()}"
        r = push_to_notion(orig_url, cover_url, label)
        if r.status_code == 200:
            return jsonify(ok=True)
        else:
            return jsonify(ok=False, error=f"Notion {r.status_code}: {r.text[:80]}")
    except Exception as e:
        return jsonify(ok=False, error=str(e)[:100])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
