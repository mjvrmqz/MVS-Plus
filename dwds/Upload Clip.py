#!/usr/bin/env python3
import subprocess, sys, os, io, threading, requests, ctypes, tempfile
import os
from pathlib import Path
 
def pip(*pkgs):
    for p in pkgs:
        subprocess.check_call([sys.executable, "-m", "pip", "install", p, "--break-system-packages", "-q"])
 
try:
    import objc
    from AppKit import NSApplication
except ImportError:
    print("Installing PyObjC..."); pip("pyobjc-core", "pyobjc-framework-Cocoa")
    import objc
 
try:
    from PIL import Image, ImageFilter, ImageEnhance
except ImportError:
    pip("Pillow"); from PIL import Image, ImageFilter, ImageEnhance
 
import objc
from AppKit import (
    NSApplication, NSWindow, NSView, NSTextField,
    NSColor, NSBezierPath, NSFont, NSBackingStoreBuffered,
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSFilenamesPboardType,
    NSDragOperationCopy, NSScreen, NSApp,
    NSFontAttributeName, NSForegroundColorAttributeName,
    NSParagraphStyleAttributeName, NSMutableParagraphStyle,
    NSTextAlignmentCenter, NSAttributedString,
)
from Foundation import NSMakeRect, NSMakePoint, NSObject
 
NOTION_KEY = os.environ.get("NOTION_KEY", "")
CLIPS_DB_ID  = os.environ.get("CLIPS_DB_ID", "")
NOTION_HDR   = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
 
VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm", ".mxf", ".wmv")
 
def c(r, g, b, a=1.0):
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(r/255, g/255, b/255, a)
 
def upload_bytes(data, filename, mime):
    import base64
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
        if os.path.isfile(tmp_path):
            os.unlink(tmp_path)
 
def make_cover(video_path):
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
        if buf.tell() < 5 * 1024 * 1024:
            break
    return buf.getvalue()
 
def get_next_inspiration_number():
    payload = {"filter": {"property": "title", "title": {"starts_with": "Inspiration "}}}
    r = requests.post(f"https://api.notion.com/v1/databases/{CLIPS_DB_ID}/query",
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
 
def push_to_notion(cover_url, filename, label):
    r = requests.get(f"https://api.notion.com/v1/databases/{CLIPS_DB_ID}", headers=NOTION_HDR)
    title_prop = "Name"
    if r.status_code == 200:
        for k, v in r.json().get("properties", {}).items():
            if v.get("type") == "title": title_prop = k; break
    payload = {
        "parent":  {"database_id": CLIPS_DB_ID},
        "cover":   {"type": "external", "external": {"url": cover_url}},
        "properties": {title_prop: {"title": [{"text": {"content": label}}]}},
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": filename}}]
                }
            }
        ],
    }
    return requests.post("https://api.notion.com/v1/pages", headers=NOTION_HDR, json=payload)
 
def process(filepath, view):
    try:
        filepath = filepath.strip().strip("{}")
        if not os.path.isfile(filepath): view.apply_state("error", "File not found"); return
        ext = Path(filepath).suffix.lower()
        if ext not in VIDEO_EXTS: view.apply_state("error", f"Unsupported: {ext}"); return
        view.update_status("Extracting first frame…", 0.15)
        cover_bytes = make_cover(filepath)
        view.update_status("Uploading cover…", 0.50)
        cover_url = upload_bytes(cover_bytes, "cover.jpg", "image/jpeg")
        view.update_status("Pushing to Notion…", 0.80)
        label = f"Inspiration {get_next_inspiration_number()}"
        filename = Path(filepath).name
        r = push_to_notion(cover_url, filename, label)
        if r.status_code == 200:
            view.apply_state("done", "✓  Added to Notion!", 1.0)
        else:
            try: msg = r.json().get("message", "")[:80]
            except: msg = r.text[:80]
            view.apply_state("error", f"Notion {r.status_code}: {msg}")
    except Exception as e:
        view.apply_state("error", str(e)[:100])
 
class DropView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(DropView, self).initWithFrame_(frame)
        if self:
            self._state = "idle"; self._status = "Drop a video here"
            self._progress = 0.0; self._callback = None
            self.registerForDraggedTypes_([NSFilenamesPboardType])
        return self
 
    def draggingEntered_(self, sender):
        if self._state in ("idle", "done", "error"):
            self._state = "hover"; self.setNeedsDisplay_(True)
        return NSDragOperationCopy
 
    def draggingExited_(self, sender):
        if self._state == "hover": self._state = "idle"; self.setNeedsDisplay_(True)
 
    def prepareForDragOperation_(self, sender): return True
 
    def performDragOperation_(self, sender):
        pb = sender.draggingPasteboard()
        paths = pb.propertyListForType_(NSFilenamesPboardType)
        if paths and self._callback:
            self._state = "working"; self._status = "Starting…"; self._progress = 0.05
            self.setNeedsDisplay_(True)
            cb = self._callback; path = paths[0]
            threading.Thread(target=cb, args=(path,), daemon=True).start()
        return True
 
    def update_status(self, msg, progress=None):
        self._status = msg
        if progress is not None: self._progress = progress
        self.performSelectorOnMainThread_withObject_waitUntilDone_(b"_redraw", None, False)
 
    def apply_state(self, state, msg="", progress=None):
        self._state = state; self._status = msg
        if progress is not None: self._progress = progress
        self.performSelectorOnMainThread_withObject_waitUntilDone_(b"_redraw", None, False)
        if state == "done":
            threading.Timer(3.0, lambda: self.performSelectorOnMainThread_withObject_waitUntilDone_(b"_reset", None, False)).start()
 
    def _redraw(self): self.setNeedsDisplay_(True)
 
    def _reset(self):
        self._state = "idle"; self._status = "Drop a video here"; self._progress = 0.0
        self.setNeedsDisplay_(True)
 
    def drawRect_(self, rect):
        w = rect.size.width; h = rect.size.height; cx = w/2; cy = h/2
        bg_map = {"idle": c(22,22,22), "hover": c(18,35,18), "working": c(22,22,22), "done": c(12,26,12), "error": c(26,12,12)}
        bg_map.get(self._state, c(22,22,22)).setFill(); NSBezierPath.fillRect_(rect)
        inset = NSMakeRect(6, 6, w-12, h-12)
        border = c(55,100,55) if self._state == "hover" else c(44,44,44)
        path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(inset, 10, 10)
        border.setStroke(); path.setLineWidth_(1.0)
        da = (ctypes.c_double * 2)(6.0, 4.0); path.setLineDash_count_phase_(da, 2, 0.0); path.stroke()
        para = NSMutableParagraphStyle.alloc().init(); para.setAlignment_(NSTextAlignmentCenter)
        def txt(s, y, fh, font, color):
            a = {NSFontAttributeName: font, NSForegroundColorAttributeName: color, NSParagraphStyleAttributeName: para}
            NSAttributedString.alloc().initWithString_attributes_(s, a).drawInRect_(NSMakeRect(10, y, w-20, fh))
        if self._state in ("idle","hover"):
            ac = c(55,100,55) if self._state=="hover" else c(44,44,44)
            arr = NSBezierPath.bezierPath()
            arr.moveToPoint_(NSMakePoint(cx, cy+28)); arr.lineToPoint_(NSMakePoint(cx, cy-8))
            arr.moveToPoint_(NSMakePoint(cx-11, cy+14)); arr.lineToPoint_(NSMakePoint(cx, cy+28)); arr.lineToPoint_(NSMakePoint(cx+11, cy+14))
            bas = NSBezierPath.bezierPath(); bas.moveToPoint_(NSMakePoint(cx-16, cy-8)); bas.lineToPoint_(NSMakePoint(cx+16, cy-8))
            for p in (arr, bas): ac.setStroke(); p.setLineWidth_(2.0); p.setLineCapStyle_(1); p.stroke()
            lbl = "Drop video here" if self._state=="idle" else "Release to add"
            lc = c(70,70,70) if self._state=="idle" else c(75,160,75)
            txt(lbl, cy-44, 22, NSFont.systemFontOfSize_(14), lc)
            txt("MP4 · MOV · MKV · AVI · M4V · WEBM", cy-64, 18, NSFont.systemFontOfSize_(10), c(40,40,40))
        elif self._state == "working":
            txt(self._status, cy-8, 22, NSFont.systemFontOfSize_(13), c(160,160,160))
            by = cy-32; bx = 40; bw = w-80
            tr = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(NSMakeRect(bx,by,bw,3),1.5,1.5)
            c(38,38,38).setFill(); tr.fill()
            fw = max(0.0, bw*self._progress)
            if fw > 0:
                fi = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(NSMakeRect(bx,by,fw,3),1.5,1.5)
                c(255,0,51).setFill(); fi.fill()
        elif self._state in ("done","error"):
            sym = "✓" if self._state=="done" else "✕"
            sc = c(55,190,55) if self._state=="done" else c(190,55,55)
            txt(sym, cy+2, 44, NSFont.boldSystemFontOfSize_(36), sc)
            txt(self._status, cy-22, 22, NSFont.systemFontOfSize_(11), c(160,160,160))
 
class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notif):
        screen = NSScreen.mainScreen().frame(); sw,sh = screen.size.width, screen.size.height
        ww,wh = 440,360; wx=(sw-ww)/2; wy=(sh-wh)/2
        style = NSWindowStyleMaskTitled|NSWindowStyleMaskClosable|NSWindowStyleMaskMiniaturizable
        self.win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(wx,wy,ww,wh), style, NSBackingStoreBuffered, False)
        self.win.setTitle_("MSV Studios · Inspiration")
        self.win.setBackgroundColor_(c(14,14,14))
        content = self.win.contentView()
        hdr = NSView.alloc().initWithFrame_(NSMakeRect(0, wh-50, ww, 50))
        hdr.setWantsLayer_(True); hdr.layer().setBackgroundColor_(c(10,10,10).CGColor())
        content.addSubview_(hdr)
        t = NSTextField.alloc().initWithFrame_(NSMakeRect(18,14,220,22))
        t.setStringValue_("Inspiration Drop"); t.setFont_(NSFont.boldSystemFontOfSize_(13))
        t.setTextColor_(c(235,235,235)); t.setBezeled_(False); t.setDrawsBackground_(False)
        t.setEditable_(False); t.setSelectable_(False); hdr.addSubview_(t)
        s = NSTextField.alloc().initWithFrame_(NSMakeRect(ww-118,16,100,18))
        s.setStringValue_("MSV Studios"); s.setFont_(NSFont.systemFontOfSize_(10))
        s.setTextColor_(c(70,70,70)); s.setAlignment_(2); s.setBezeled_(False)
        s.setDrawsBackground_(False); s.setEditable_(False); s.setSelectable_(False); hdr.addSubview_(s)
        m=18; dh=wh-50-m*2
        self.dv = DropView.alloc().initWithFrame_(NSMakeRect(m,m,ww-m*2,dh))
        self.dv._callback = lambda p: process(p, self.dv)
        content.addSubview_(self.dv)
        self.win.makeKeyAndOrderFront_(None); NSApp.activateIgnoringOtherApps_(True)
 
    def applicationShouldTerminateAfterLastWindowClosed_(self, app): return True
 
if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()
