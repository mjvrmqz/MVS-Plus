#!/usr/bin/env python3
import subprocess, sys, os, io, threading, requests, ctypes
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

NOTION_TOKEN = "ntn_U60582391564u7rDIIxeSyYXMD7aOqEaawu30A8D3wUag7"
DATABASE_ID  = "3531691964b480ca8a4cf0dfcd109915"
YT_ICON      = ("https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/YouTube_full-color_icon_%282017%29.svg/320px-YouTube_full-color_icon_%282017%29.svg.png")
NOTION_HDR   = {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

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

def upload_file(path):
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    return upload_bytes(open(path, "rb").read(), Path(path).name, mime)

def make_cover(path):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    th = int(w * 2 / 5)
    if th < h:
        top = (h - th) // 2
        img = img.crop((0, top, w, top + th))
    img = img.resize((1500, 600), Image.LANCZOS)
    img = img.filter(ImageFilter.GaussianBlur(radius=18))
    img = ImageEnhance.Brightness(img).enhance(0.38)
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=88)
    return buf.getvalue()

def get_next_inspiration_number():
    payload = {"filter": {"property": "title", "title": {"starts_with": "Inspiration "}}}
    r = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
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
    r = requests.get(f"https://api.notion.com/v1/databases/{DATABASE_ID}", headers=NOTION_HDR)
    title_prop = "Name"
    if r.status_code == 200:
        for k, v in r.json().get("properties", {}).items():
            if v.get("type") == "title": title_prop = k; break
    payload = {
        "parent":  {"database_id": DATABASE_ID},
        "cover":   {"type": "external", "external": {"url": cover_url}},
        "properties": {title_prop: {"title": [{"text": {"content": label}}]}},
        "children": [{"object": "block", "type": "image", "image": {"type": "external", "external": {"url": orig_url}}}],
    }
    return requests.post("https://api.notion.com/v1/pages", headers=NOTION_HDR, json=payload)

def process(filepath, view):
    try:
        filepath = filepath.strip().strip("{}")
        if not os.path.isfile(filepath): view.apply_state("error", "File not found"); return
        ext = Path(filepath).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"): view.apply_state("error", f"Unsupported: {ext}"); return
        view.update_status("Uploading image\u2026", 0.15)
        orig_url = upload_file(filepath)
        view.update_status("Creating cover\u2026", 0.45)
        cover_bytes = make_cover(filepath)
        view.update_status("Uploading cover\u2026", 0.65)
        cover_url = upload_bytes(cover_bytes, "cover.jpg", "image/jpeg")
        view.update_status("Pushing to Notion\u2026", 0.85)
        label = f"Inspiration {get_next_inspiration_number()}"
        r = push_to_notion(orig_url, cover_url, label)
        if r.status_code == 200:
            view.apply_state("done", "\u2713  Added to Notion!", 1.0)
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
            self._state = "idle"; self._status = "Drop an image here"
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
            self._state = "working"; self._status = "Starting\u2026"; self._progress = 0.05
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
        self._state = "idle"; self._status = "Drop an image here"; self._progress = 0.0
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
            lbl = "Drop image here" if self._state=="idle" else "Release to add"
            lc = c(70,70,70) if self._state=="idle" else c(75,160,75)
            txt(lbl, cy-44, 22, NSFont.systemFontOfSize_(14), lc)
            txt("JPG \u00b7 PNG \u00b7 WEBP", cy-64, 18, NSFont.systemFontOfSize_(10), c(40,40,40))
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
            sym = "\u2713" if self._state=="done" else "\u2715"
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
        self.win.setTitle_("MSV Studios \u00b7 Inspiration")
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
