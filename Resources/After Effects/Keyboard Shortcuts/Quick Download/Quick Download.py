#!/usr/bin/env python3
"""
AE Loader - PyQt6 version
"""

import sys, os, json, subprocess
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.multimedia.*=false"
import ctypes
if sys.platform == "darwin":
    sys.stderr = open(os.devnull, "w")
import urllib.request, io

from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QSplitter, QComboBox, QCheckBox, QFileDialog, QSpinBox,
    QFrame, QSizePolicy, QProgressBar, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QMenu, QStyledItemDelegate
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QUrl, QTimer, QPoint, QRect
from PyQt6.QtGui import QPixmap, QImage, QFont, QColor, QIcon, QPainter, QPainterPath

BG    = "#1a0000"
CARD  = "#1a1a1a"
ACC   = "#ff0000"
FG    = "#e8e8e8"
SUB   = "#888888"
DARK  = "#2a2a2a"
GREY  = "#2d2d2d"

AE_LABELS = [
    ("None",       None),
    ("Red",        "#E4573C"),
    ("Yellow",     "#E4D84B"),
    ("Aqua",       "#43C9C3"),
    ("Pink",       "#E47BB4"),
    ("Lavender",   "#9B89C4"),
    ("Peach",      "#E4A56B"),
    ("Sea Foam",   "#5EC4A1"),
    ("Blue",       "#4B9BE4"),
    ("Green",      "#6BBF5E"),
    ("Purple",     "#7B4BE4"),
    ("Orange",     "#E4873C"),
    ("Brown",      "#9B6B3C"),
    ("Fuchsia",    "#E43CA5"),
    ("Cyan",       "#3CE4D8"),
    ("Sandstone",  "#C4A57B"),
    ("Dark Green", "#3C7B4B"),
]



class SimpleComboDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        from PyQt6.QtWidgets import QStyle
        painter.save()
        is_sel = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hov = bool(option.state & QStyle.StateFlag.State_MouseOver)
        if is_sel or is_hov:
            painter.fillRect(option.rect, QColor("#ff0000"))
        else:
            painter.fillRect(option.rect, QColor("#1a1a1a"))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(option.rect.adjusted(8, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, index.data())
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(100, 22)

class ColorLabelDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        from PyQt6.QtWidgets import QStyle
        is_sel = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hov = bool(option.state & QStyle.StateFlag.State_MouseOver)
        if is_sel or is_hov:
            painter.fillRect(option.rect, QColor("#ff0000"))
        else:
            painter.fillRect(option.rect, QColor("#1a1a1a"))
        color_hex = index.data(Qt.ItemDataRole.UserRole)
        swatch_rect = QRect(option.rect.left() + 6, option.rect.top() + 4, 12, 12)
        if color_hex:
            painter.setBrush(QColor(color_hex))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(swatch_rect, 2, 2)
        else:
            painter.setBrush(QColor("#333333"))
            painter.setPen(QColor("#555555"))
            painter.drawRoundedRect(swatch_rect, 2, 2)
        painter.setPen(QColor("#ffffff"))
        text_rect = option.rect.adjusted(26, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, index.data())
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(100, 20)

import os as _os
_BASE = _os.path.dirname(_os.path.abspath(__file__)) if not getattr(_os.sys, "frozen", False) else _os.path.dirname(_os.sys.executable)
LOGO_PATH      = _os.path.join(_BASE, "AE Loader Logo.png")
PRESETS_PATH   = _os.path.join(_BASE, "ae_loader_presets.json")
BOOKMARKS_PATH = _os.path.join(_BASE, "ae_loader_bookmarks.json")

STYLE = f"""
QWidget {{
    background-color: {BG};
    color: {FG};
    font-family: "Helvetica Neue";
    font-size: 11px;
}}
QLabel {{ background: transparent; }}
QLineEdit {{
    background: #ffffff;
    color: #000000;
    border: none;
    border-radius: 2px;
    padding: 6px 10px;
    font-size: 13px;
}}
QPushButton {{
    background: {DARK};
    color: {FG};
    border: none;
    border-radius: 3px;
    padding: 6px 14px;
    font-family: "Helvetica Neue";
    font-size: 11px;
}}
QPushButton:hover {{ background: #333333; }}
QPushButton#search_btn {{
    background: #f5e642;
    color: #111111;
    font-weight: bold;
    font-size: 12px;
    padding: 7px 20px;
}}
QPushButton#search_btn:hover {{ background: #ffe500; }}
QPushButton#dl_btn {{
    background: #f5e642;
    color: #111111;
    font-weight: bold;
    font-size: 13px;
    padding: 8px;
    border-radius: 0px;
}}
QPushButton#dl_btn:hover {{ background: #ffe500; }}
QPushButton#dl_btn:disabled {{ background: #ccc020; color: rgba(0,0,0,0.4); }}
QComboBox {{
    background: {DARK};
    color: #ffffff;
    border: none;
    border-radius: 3px;
    padding: 4px 8px;
    font-size: 10px;
    font-family: "Helvetica Neue";
}}
QComboBox:hover {{ background: {ACC}; color: white; }}
QComboBox::drop-down {{ border: none; width: 16px; }}
QComboBox QAbstractItemView {{
    background: {DARK};
    color: {FG};
    border: none;
    outline: none;
}}
QComboBox QAbstractItemView::item {{ padding: 4px 8px; }}
QComboBox QAbstractItemView::item:hover {{ background: {ACC}; color: white; }}
QComboBox QAbstractItemView::item:focus {{ background: {ACC}; color: white; }}
QComboBox QAbstractItemView::item:selected {{ background: {ACC}; color: white; }}
QScrollBar:vertical {{
    background: {CARD};
    width: 5px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: #444;
    border-radius: 2px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QSplitter::handle {{ background: #222; }}
QTreeWidget {{
    background: {CARD};
    border: none;
    outline: none;
}}
QTreeWidget QScrollBar {{
    background: {CARD};
}}
QTreeWidget > QWidget {{
    background: {CARD};
}}
QTreeWidget::item {{
    padding: 3px 4px;
    border: none;
    color: {FG};
    font-family: "Helvetica Neue";
}}
QTreeWidget::item:selected {{ background: {ACC}; color: white; border-radius: 6px; }}
QTreeWidget::item:hover:!selected {{ background: #252525; }}
QTreeWidget::branch {{ background: {CARD}; }}
QTreeWidget {{ background: {CARD}; }}
"""

def seconds_to_hms(s):
    s = int(s or 0)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"

def hms_to_seconds(hms):
    parts = hms.strip().split(":")
    try:
        parts = [int(p) for p in parts]
        if len(parts) == 3: return parts[0]*3600 + parts[1]*60 + parts[2]
        if len(parts) == 2: return parts[0]*60 + parts[1]
        return int(parts[0])
    except: return 0

def get_thumb_url(info):
    vid_id = info.get("id", "")
    if vid_id:
        return f"https://i.ytimg.com/vi/{vid_id}/maxresdefault.jpg|https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
    for t in (info.get("thumbnails") or [])[::-1]:
        u = t.get("url", "")
        if u.startswith("http"): return u
    return info.get("thumbnail")

def make_placeholder_pixmap(w=80, h=45):
    pix = QPixmap(w, h)
    pix.fill(QColor("#2a2a2a"))
    p = QPainter(pix)
    p.setPen(QColor("#444444"))
    p.setFont(QFont("Helvetica Neue", 8))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "No Preview")
    p.end()
    rounded = QPixmap(pix.size())
    rounded.fill(Qt.GlobalColor.transparent)
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, w, h, 5, 5)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pix)
    painter.end()
    return rounded

def load_pixmap(url, w=80, h=45):
    urls = url.split("|") if url and "|" in url else [url]
    screen = QApplication.primaryScreen()
    ratio = screen.devicePixelRatio() if screen else 2.0
    pw, ph = int(w * ratio), int(h * ratio)
    for u in urls:
        try:
            with urllib.request.urlopen(u, timeout=8) as r:
                data = r.read()
            img = QImage()
            img.loadFromData(data)
            if img.isNull(): continue
            pix = QPixmap.fromImage(img)
            pix = pix.scaled(pw, ph, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
            rounded = QPixmap(pix.size())
            rounded.fill(Qt.GlobalColor.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(0, 0, pix.width(), pix.height(), 8 * ratio, 8 * ratio)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pix)
            painter.end()
            rounded.setDevicePixelRatio(ratio)
            return rounded
        except:
            continue
    return make_placeholder_pixmap(w, h)


def make_play_icon(size=16, color="#ffffff"):
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)
    from PyQt6.QtGui import QPolygonF
    from PyQt6.QtCore import QPointF
    triangle = QPolygonF([QPointF(3, 2), QPointF(3, size-2), QPointF(size-2, size/2)])
    p.drawPolygon(triangle)
    p.end()
    return QIcon(pix)

def make_pause_icon(size=16, color="#ffffff"):
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)
    bar_w = max(3, size // 4)
    gap = max(2, size // 5)
    x1 = (size - bar_w*2 - gap) // 2
    x2 = x1 + bar_w + gap
    p.drawRoundedRect(x1, 2, bar_w, size-4, 1, 1)
    p.drawRoundedRect(x2, 2, bar_w, size-4, 1, 1)
    p.end()
    return QIcon(pix)

def make_mute_icon(size=16, muted=False, color="#ffffff"):
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)
    from PyQt6.QtGui import QPolygonF, QPen
    from PyQt6.QtCore import QPointF, QRectF
    cx = size * 0.35
    speaker = QPolygonF([
        QPointF(2, size*0.35), QPointF(cx, size*0.35),
        QPointF(cx + size*0.2, size*0.15), QPointF(cx + size*0.2, size*0.85),
        QPointF(cx, size*0.65), QPointF(2, size*0.65)
    ])
    p.drawPolygon(speaker)
    if not muted:
        p.setBrush(Qt.BrushStyle.NoBrush)
        wp = QPen(QColor(color), 1.5)
        wp.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(wp)
        p.drawArc(QRectF(size*0.55, size*0.25, size*0.2, size*0.5), -30*16, 60*16)
        p.drawArc(QRectF(size*0.65, size*0.15, size*0.25, size*0.7), -30*16, 60*16)
    else:
        xp = QPen(QColor("#ff4444"), 1.5)
        xp.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(xp)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(int(size*0.62), int(size*0.3), int(size*0.88), int(size*0.7))
        p.drawLine(int(size*0.88), int(size*0.3), int(size*0.62), int(size*0.7))
    p.end()
    return QIcon(pix)



def make_comment_icon(size=16, color="#888888"):
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    from PyQt6.QtGui import QPen, QPainterPath
    from PyQt6.QtCore import QRectF, QPointF
    from PyQt6.QtGui import QPolygonF
    # Bubble outline
    pen = QPen(QColor(color), 1.5)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(1, 1, size-2, size*0.72), 3, 3)
    # Tail
    p.drawLine(int(size*0.2), int(size*0.72), int(size*0.2), int(size*0.92))
    p.drawLine(int(size*0.2), int(size*0.92), int(size*0.5), int(size*0.72))
    # Lines inside bubble
    p.setPen(QPen(QColor(color), 1.2))
    p.drawLine(int(size*0.25), int(size*0.28), int(size*0.75), int(size*0.28))
    p.drawLine(int(size*0.25), int(size*0.48), int(size*0.62), int(size*0.48))
    p.end()
    return QIcon(pix)


def make_thumb_icon(size=12, color="#888888"):
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    from PyQt6.QtGui import QPen
    pen = QPen(QColor(color), 1.5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    # Simple thumb outline
    from PyQt6.QtCore import QRectF
    p.drawLine(int(size*0.1), int(size*0.5), int(size*0.1), int(size*0.92))
    p.drawLine(int(size*0.1), int(size*0.92), int(size*0.9), int(size*0.92))
    p.drawLine(int(size*0.9), int(size*0.92), int(size*0.9), int(size*0.5))
    p.drawLine(int(size*0.9), int(size*0.5), int(size*0.55), int(size*0.5))
    p.drawLine(int(size*0.55), int(size*0.5), int(size*0.7), int(size*0.08))
    p.drawLine(int(size*0.7), int(size*0.08), int(size*0.45), int(size*0.08))
    p.drawLine(int(size*0.45), int(size*0.08), int(size*0.3), int(size*0.5))
    p.drawLine(int(size*0.3), int(size*0.5), int(size*0.1), int(size*0.5))
    p.end()
    return pix

def make_gear_icon(size=16, color="#888888"):
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    from PyQt6.QtCore import QRectF
    import math
    cx, cy, r_out, r_in = size/2, size/2, size*0.42, size*0.22
    teeth = 8
    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)
    from PyQt6.QtGui import QPainterPath
    path = QPainterPath()
    for i in range(teeth):
        angle = 2 * math.pi * i / teeth
        angle2 = 2 * math.pi * (i + 0.4) / teeth
        angle3 = 2 * math.pi * (i + 0.6) / teeth
        angle4 = 2 * math.pi * (i + 1) / teeth
        path.moveTo(cx + r_in * math.cos(angle), cy + r_in * math.sin(angle))
        path.lineTo(cx + r_out * math.cos(angle), cy + r_out * math.sin(angle))
        path.lineTo(cx + r_out * math.cos(angle2), cy + r_out * math.sin(angle2))
        path.lineTo(cx + r_out * 1.25 * math.cos((angle+angle2)/2), cy + r_out * 1.25 * math.sin((angle+angle2)/2))
        path.lineTo(cx + r_out * math.cos(angle3), cy + r_out * math.sin(angle3))
        path.lineTo(cx + r_out * math.cos(angle4), cy + r_out * math.sin(angle4))
        path.lineTo(cx + r_in * math.cos(angle4), cy + r_in * math.sin(angle4))
    path.closeSubpath()
    p.drawPath(path)
    # Center hole
    p.setBrush(QColor(0,0,0,0))
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
    p.drawEllipse(QRectF(cx-r_in*0.8, cy-r_in*0.8, r_in*1.6, r_in*1.6))
    p.end()
    return QIcon(pix)

def make_logo(height):
    pix = QPixmap(LOGO_PATH)
    if pix.isNull():
        return None
    screen = QApplication.primaryScreen()
    ratio = screen.devicePixelRatio() if screen else 2.0
    scaled = pix.scaledToHeight(int(height * ratio), Qt.TransformationMode.SmoothTransformation)
    scaled.setDevicePixelRatio(ratio)
    return scaled

def load_bookmarks():
    try:
        with open(BOOKMARKS_PATH) as f:
            return json.load(f)
    except:
        return []

def save_bookmarks(bookmarks):
    try:
        with open(BOOKMARKS_PATH, "w") as f:
            json.dump(bookmarks, f, indent=2)
    except:
        pass

def load_presets():
    try:
        with open(PRESETS_PATH) as f:
            return json.load(f)
    except:
        return []

def save_presets(presets):
    try:
        with open(PRESETS_PATH, "w") as f:
            json.dump(presets, f, indent=2)
    except:
        pass


def fetch_channel_info(query):
    try:
        cmd = ["yt-dlp", "--dump-single-json", "--flat-playlist", "--no-warnings", query]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        data = json.loads(r.stdout)
        channel = data.get("uploader") or data.get("channel") or data.get("title") or ""
        avatar = None
        for t in (data.get("thumbnails") or [])[::-1]:
            u = t.get("url", "")
            if u.startswith("http"):
                avatar = u
                break
        if channel:
            return {"name": channel, "avatar": avatar}
    except:
        pass
    return None



def run_ae_import(file_path, import_at="Playhead", label_color=None, clip_name=""):
    import_at_code = {
        "Playhead": "comp.time",
        "Start": "0",
        "End": "comp.duration - (layer.outPoint - layer.inPoint)"
    }.get(import_at, "comp.currentTime")

    fp = file_path.replace("\\", "/").replace("'", "\\'")
    jsx = (
        "#target aftereffects\n"
        "(function() {\n"
        "var file = new File('" + fp + "');\n"
        "if (!file.exists) { alert('File not found: ' + file.fsName); return; }\n"
        "var io = new ImportOptions(file);\n"
        "var item = app.project.importFile(io);\n"
        "var comp = app.project.activeItem;\n"
        "if (!comp || !(comp instanceof CompItem)) { return; }\n"
        "var layer = comp.layers.add(item);\n"
        "layer.startTime = " + import_at_code + ";\n"
        + (("layer.label = " + str({
            "#E4573C":1,"#E4D84B":2,"#43C9C3":3,"#E47BB4":4,
            "#9B89C4":5,"#E4A56B":6,"#5EC4A1":7,"#4B9BE4":8,
            "#6BBF5E":9,"#7B4BE4":10,"#E4873C":11,"#9B6B3C":12,
            "#E43CA5":13,"#3CE4D8":14,"#C4A57B":15,"#3C7B4B":16
        }.get((label_color or "").upper(), 0)) + ";\n") if label_color else "")
        + (("layer.name = '" + clip_name.replace("'", "\\'") + "';\n") if clip_name else "")
        + "})();\n"
    )
    import subprocess, os
    jsx_path = os.path.expanduser("~/ae_loader_import.jsx")
    with open(jsx_path, "w", encoding="utf-8-sig") as f:
        f.write(jsx)
    try:
        subprocess.run(
            ["osascript",
             "-e", 'tell application "Adobe After Effects 2025" to activate',
             "-e", f'tell application "Adobe After Effects 2025" to DoScriptFile "{jsx_path}"'],
            timeout=15
        )
    except Exception as e:
        print(f"AE import error: {e}")




class ChannelInfoWorker(QThread):
    done = pyqtSignal(dict)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            cmd = ["yt-dlp", "--dump-single-json", "--flat-playlist",
                   "--playlist-end", "1", "--no-warnings", self.query]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            data = json.loads(r.stdout)
            # Get avatar url
            avatar_url = ""
            for t in (data.get("thumbnails") or [])[::-1]:
                u = t.get("url", "")
                if u.startswith("http"):
                    avatar_url = u
                    break
            self.done.emit({
                "name": data.get("uploader") or data.get("channel") or data.get("title") or "",
                "handle": data.get("uploader_id") or "",
                "subs": data.get("channel_follower_count") or 0,
                "avatar": avatar_url,
            })
        except Exception as e:
            print(f"ChannelInfoWorker error: {e}")
            self.done.emit({})

class VideoItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        from PyQt6.QtWidgets import QStyle
        from PyQt6.QtCore import QRect
        painter.save()

        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        is_category = not index.parent().isValid()

        if is_category:
            # Let Qt handle category items normally
            super().paint(painter, option, index)
            painter.restore()
            return

        # Background
        if is_selected:
            bg = QColor(ACC)
        elif is_hover:
            bg = QColor(255, 255, 255, 20)
        else:
            bg = QColor(0, 0, 0, 0)

        r = option.rect
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRoundedRect(r.x()+2, r.y()+2, r.width()-4, r.height()-4, 6, 6)
        painter.fillPath(path, bg)

        # Icon
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        icon_w, icon_h = 96, 54
        icon_x = r.left() + 20
        icon_y = r.top() + (r.height() - icon_h) // 2
        if icon and not icon.isNull():
            icon.paint(painter, icon_x, icon_y, icon_w, icon_h)

        # Text
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        lines = text.split("\n", 1)
        tx = icon_x + icon_w + 10


        # Title - max 2 lines with ellipsis
        painter.setFont(QFont("Helvetica Neue", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#ffffff"))
        fm_title = painter.fontMetrics()
        title_text = lines[0] if lines else ""
        line_h = fm_title.lineSpacing()
        max_title_h = line_h * 2
        title_rect = QRect(tx, r.top() + 6, r.right() - tx - 4, max_title_h)
        elided = fm_title.elidedText(title_text, Qt.TextElideMode.ElideRight, title_rect.width() * 2)
        # Draw word wrapped but max 2 lines
        words = title_text.split()
        line1, line2 = "", ""
        for w in words:
            test = (line1 + " " + w).strip()
            if fm_title.horizontalAdvance(test) <= title_rect.width():
                line1 = test
            else:
                rest = title_text[len(line1):].strip()
                line2 = fm_title.elidedText(rest, Qt.TextElideMode.ElideRight, title_rect.width())
                break
        painter.drawText(QRect(tx, r.top() + 12, r.right() - tx - 4, line_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, line1)
        if line2:
            painter.drawText(QRect(tx, r.top() + 12 + line_h, r.right() - tx - 4, line_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, line2)
        title_bottom = r.top() + 12 + (line_h * 2 if line2 else line_h)

        # Meta - sits right below title
        if len(lines) > 1:
            painter.setFont(QFont("Helvetica Neue", 8, QFont.Weight.Bold))
            painter.setPen(QColor("#ffffff") if is_selected else QColor("#777777"))
            meta_rect = QRect(tx, title_bottom + 2, r.right() - tx - 4, 14)
            painter.drawText(meta_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, lines[1])

        painter.restore()

    def sizeHint(self, option, index):
        if not index.parent().isValid():
            return QSize(0, 22)
        return QSize(0, 80)



class CustomPopup(QWidget):
    selected = pyqtSignal(str)

    def __init__(self, options, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.options = options
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        container = QWidget()
        container.setStyleSheet("background: #1a1a1a; border-radius: 6px;")
        cl = QVBoxLayout(container)
        cl.setContentsMargins(4, 4, 4, 4)
        cl.setSpacing(1)
        for opt in self.options:
            btn = QPushButton(opt)
            btn.setStyleSheet("""
                QPushButton { background: transparent; color: #ffffff; border: none; border-radius: 3px;
                              padding: 6px 12px; font-size: 10px; font-family: "Helvetica Neue"; text-align: left; }
                QPushButton:hover { background: #ff0000; color: white; }
            """)
            btn.clicked.connect(lambda checked, o=opt: (self.selected.emit(o), self.hide()))
            cl.addWidget(btn)
        layout.addWidget(container)
        self.setFixedWidth(max(120, max(len(o) for o in self.options) * 7 + 24))

    def show_at(self, widget):
        pos = widget.mapToGlobal(widget.rect().bottomLeft())
        self.move(pos)
        self.show()
        self.raise_()


def make_menu_btn(parent, options, default=None, width=None):
    btn = QPushButton(default or options[0])
    if width: btn.setFixedWidth(width)
    btn.setStyleSheet("background: #1a1a1a; color: #ffffff; border: none; border-radius: 3px; padding: 4px 8px; font-size: 10px; font-family: \'Helvetica Neue\'; text-align: left;")
    btn._value = default or options[0]
    btn._options = options
    popup = CustomPopup(options, parent)
    def on_select(val):
        btn.setText(val)
        btn._value = val
        if hasattr(btn, "_on_change"):
            btn._on_change()
    popup.selected.connect(on_select)
    btn.clicked.connect(lambda: popup.show_at(btn))
    btn.currentText = lambda: btn._value
    btn.setCurrentText = lambda v: (btn.setText(v), setattr(btn, "_value", v))
    btn.findText = lambda v: btn._options.index(v) if v in btn._options else -1
    btn.setCurrentIndex = lambda i: (btn.setText(btn._options[i]), setattr(btn, "_value", btn._options[i])) if 0 <= i < len(btn._options) else None
    return btn

class DragTimecode(QLineEdit):
    timeChanged = pyqtSignal(int)

    def __init__(self, text="00:00:00", parent=None):
        super().__init__(text, parent)
        self._drag_start_x = None
        self._drag_start_secs = 0
        self._dragging = False
        self.setStyleSheet("background: #1a1a1a; color: #ffffff; padding: 3px 6px; font-size: 10px;")
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setReadOnly(True)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start_x = e.position().x()
            self._drag_start_secs = hms_to_seconds(self.text())
            self._dragging = True
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._dragging and self._drag_start_x is not None and (e.buttons() & Qt.MouseButton.LeftButton):
            delta = int((e.position().x() - self._drag_start_x) / 3)
            new_secs = max(0, self._drag_start_secs + delta)
            self.setText(seconds_to_hms(new_secs))
            self.timeChanged.emit(new_secs)
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._dragging:
            self._dragging = False
            self._drag_start_x = None
            e.accept()
        else:
            super().mouseReleaseEvent(e)


class SearchWorker(QThread):
    results = pyqtSignal(list)
    error   = pyqtSignal(str)

    def __init__(self, query, limit):
        super().__init__()
        self.query = query
        self.limit = limit

    def run(self):
        q = self.query
        if "youtube.com" in q or "youtu.be" in q:
            args = ["--flat-playlist", "--dump-json", "--playlist-end", str(self.limit), q]
        else:
            args = ["--flat-playlist", "--dump-json", f"ytsearch{self.limit}:{q}"]
        cmd = ["yt-dlp", "--no-warnings", "--quiet"] + args
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            videos = []
            for line in r.stdout.splitlines():
                try:
                    v = json.loads(line)
                    if v.get("id"): videos.append(v)
                except: pass
            self.results.emit(videos)
        except Exception as e:
            self.error.emit(str(e))


class InfoWorker(QThread):
    done = pyqtSignal(dict)

    def __init__(self, v):
        super().__init__()
        self.v = v

    def run(self):
        vid_id = self.v.get("id") or self.v.get("url", "")
        url = f"https://www.youtube.com/watch?v={vid_id}" if len(vid_id) == 11 else vid_id
        cmd = ["yt-dlp", "--no-warnings", "--quiet", "--dump-json", "--no-playlist", url]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            info = json.loads(r.stdout.splitlines()[0])
            self.done.emit(info)
        except:
            self.done.emit(self.v)


class StreamWorker(QThread):
    done  = pyqtSignal(str)
    error = pyqtSignal()

    def __init__(self, vid_id):
        super().__init__()
        self.vid_id = vid_id

    def run(self):
        url = f"https://www.youtube.com/watch?v={self.vid_id}"
        cmd = ["yt-dlp", "-f", "18/best[vcodec^=avc1][height<=480]/best[ext=mp4]/best",
               "-g", "--no-playlist", "--cookies-from-browser", "chrome", "--remote-components", "ejs:github", url]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            lines = r.stdout.strip().splitlines()
            if lines:
                self.done.emit(lines[0])
            else:
                self.error.emit()
        except:
            self.error.emit()


class ThumbWorker(QThread):
    done = pyqtSignal(int, QPixmap)

    def __init__(self, idx, url):
        super().__init__()
        self.idx = idx
        self.url = url

    def run(self):
        pix = load_pixmap(self.url, 240, 135)
        if pix:
            self.done.emit(self.idx, pix)


class DownloadWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, url, out_dir, fmt, full, start, end, is_mp3=False, clip_name=""):
        super().__init__()
        self.url = url; self.out_dir = out_dir; self.fmt = fmt
        self.full = full; self.start_ts = start; self.end_ts = end
        self.is_mp3 = is_mp3; self.clip_name = clip_name

    def run(self):
        ext = "mp3" if self.is_mp3 else "mp4"
        cmd = ["yt-dlp", "-f", self.fmt, "--merge-output-format", ext,
               "-o", os.path.join(self.out_dir, f"{self.clip_name if self.clip_name else "%(title)s"}.{ext}"), "--no-warnings",
               "--print", "after_move:filepath", "--cookies-from-browser", "chrome", "--remote-components", "ejs:github"]
        if self.is_mp3:
            cmd += ["--extract-audio", "--audio-format", "mp3"]
        if not self.full:
            ss = hms_to_seconds(self.start_ts)
            ee = hms_to_seconds(self.end_ts)
            cmd += ["--download-sections", f"*{ss}-{ee}", "--force-keyframes-at-cuts"]
        cmd.append(self.url)
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            output_file = None
            for line in proc.stdout:
                line = line.strip()
                if line:
                    self.progress.emit(line)
                    # yt-dlp prints the filepath on its own line
                    if line and not line.startswith("[") and not line.startswith("ERROR") and os.path.exists(line):
                        output_file = line
            proc.wait()
            # Fallback: find most recently modified file in out_dir
            if not output_file and proc.returncode == 0:
                import glob, time
                files = glob.glob(os.path.join(self.out_dir, f"*.{ext}"))
                if files:
                    output_file = max(files, key=os.path.getmtime)
            self.finished.emit(proc.returncode == 0, output_file or "")
        except Exception as e:
            self.progress.emit(f"Error: {e}")
            self.finished.emit(False, "")




class CommentItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        from PyQt6.QtWidgets import QStyle
        painter.save()
        is_sel = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if is_sel:
            from PyQt6.QtGui import QPainterPath
            from PyQt6.QtCore import QRectF
            path = QPainterPath()
            path.addRoundedRect(QRectF(option.rect.adjusted(4, 2, -4, -2)), 6, 6)
            painter.fillPath(path, QColor(ACC))
        else:
            painter.fillRect(option.rect, QColor(GREY))

        r = option.rect
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        parts = text.split("\t", 1)
        author = parts[0] if parts else ""
        rest = parts[1] if len(parts) > 1 else ""
        rest_parts = rest.split("\n", 1)
        timestamp = rest_parts[0] if rest_parts else ""
        body = rest_parts[1] if len(rest_parts) > 1 else ""

        # Author bold
        painter.setFont(QFont("Helvetica Neue", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(r.adjusted(10, 6, -10, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, author)

        # Timestamp
        fm = painter.fontMetrics()
        author_w = fm.horizontalAdvance(author) + 8
        painter.setFont(QFont("Helvetica Neue", 8))
        painter.setPen(QColor("#888888"))
        painter.drawText(r.adjusted(10 + author_w, 6, -10, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, timestamp)

        # Body
        painter.setFont(QFont("Helvetica Neue", 9))
        painter.setPen(QColor("#ffffff") if is_sel else QColor("#e8e8e8"))
        body_parts = body.split("\n")
        body_text = body_parts[0] if body_parts else body
        likes_text = body_parts[1].strip() if len(body_parts) > 1 else ""
        painter.drawText(r.adjusted(10, 22, -10, -16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, body_text)
        # Thumb icon + likes
        if likes_text:
            painter.setFont(QFont("Helvetica Neue", 8))
            painter.setPen(QColor("#888888"))
            painter.drawText(r.adjusted(10, 0, -10, -6), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, f"♥ {likes_text.strip()}")

        painter.restore()

    def sizeHint(self, option, index):
        from PyQt6.QtGui import QFontMetrics
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        parts = text.split("\t", 1)
        rest = parts[1] if len(parts) > 1 else ""
        body = rest.split("\n", 1)[1] if "\n" in rest else ""
        fm = QFontMetrics(QFont("Helvetica Neue", 9))
        width = option.rect.width() - 20 if option.rect.width() > 0 else 400
        body_rect = fm.boundingRect(0, 0, width, 1000, Qt.TextFlag.TextWordWrap, body)
        return QSize(0, 36 + body_rect.height())

class CommentWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, vid_id):
        super().__init__()
        self.vid_id = vid_id

    def run(self):
        url = f"https://www.youtube.com/watch?v={self.vid_id}"
        cmd = ["yt-dlp", "--dump-json", "--write-comments", "--no-warnings", "--quiet",
               "--extractor-args", "youtube:comment_sort=top;max_comments=30,all,0,100"
               "--cookies-from-browser", "chrome", "--remote-components", "ejs:github", url]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            data = json.loads(r.stdout.splitlines()[0])
            comments = data.get("comments") or []
            self.done.emit(comments[:50])
        except:
            self.done.emit([])

class YTAuthWorker(QThread):
    done = pyqtSignal(dict)

    def run(self):
        try:
            cmd = ["yt-dlp", "--cookies-from-browser", "chrome", "--dump-json",
                   "--no-warnings", "--quiet", "https://www.youtube.com/feed/subscriptions"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            for line in r.stdout.splitlines():
                try:
                    data = json.loads(line)
                    name = data.get("uploader") or data.get("channel") or ""
                    avatar = ""
                    for t in (data.get("thumbnails") or [])[::-1]:
                        u = t.get("url", "")
                        if u.startswith("http"):
                            avatar = u
                            break
                    if name:
                        self.done.emit({"name": name, "avatar": avatar, "signed_in": True})
                        return
                except: continue
            self.done.emit({"signed_in": False})
        except:
            self.done.emit({"signed_in": False})

class ChannelSuggestWorker(QThread):
    results = pyqtSignal(list)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            cmd = ["yt-dlp", "--flat-playlist", "--dump-json", "--no-warnings",
                   "--quiet", f"ytsearch15:{self.query}"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            seen_channels = {}
            for line in r.stdout.splitlines():
                try:
                    v = json.loads(line)
                    channel = v.get("uploader") or v.get("channel") or ""
                    channel_url = v.get("uploader_url") or v.get("channel_url") or ""
                    channel_id = v.get("uploader_id") or v.get("channel_id") or ""
                    if not channel or channel in seen_channels: continue
                    # Get channel avatar via channel page
                    if channel_url:
                        cmd2 = ["yt-dlp", "--dump-single-json", "--flat-playlist",
                                "--playlist-end", "1", "--no-warnings", "--quiet", channel_url]
                        r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=10)
                        try:
                            data = json.loads(r2.stdout)
                            avatar = ""
                            for t in (data.get("thumbnails") or [])[::-1]:
                                u = t.get("url", "")
                                if u.startswith("http"):
                                    avatar = u
                                    break
                            subs = data.get("channel_follower_count") or 0
                        except:
                            avatar = ""
                            subs = 0
                    else:
                        avatar = ""
                        subs = 0
                    seen_channels[channel] = {
                        "name": channel,
                        "url": channel_url,
                        "avatar": avatar,
                        "subs": subs
                    }
                    if len(seen_channels) >= 3:
                        break
                except: continue
            # Sort by subs
            results = sorted(seen_channels.values(), key=lambda x: x.get("subs", 0), reverse=True)
            self.results.emit(results[:3])
        except Exception as e:
            print(f"ChannelSuggestWorker error: {e}")
            self.results.emit([])

class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AE Loader")
        self.setFixedSize(440, 420)
        self.setStyleSheet(STYLE)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self._build()
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def _build(self):
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {BG};")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.stack)

        search_page = QWidget()
        layout = QVBoxLayout(search_page)
        layout.setContentsMargins(24, 0, 24, 12)
        layout.setSpacing(6)

        # Widgets defined here
        logo_lbl = QLabel()
        logo = make_logo(32)
        if logo:
            logo_lbl.setPixmap(logo)
        else:
            logo_lbl.setText("\u25b6")
            logo_lbl.setStyleSheet(f"color: {ACC}; font-size: 16px; font-weight: bold;")
        title = QLabel("AE Loader")
        title.setStyleSheet(f"color: {FG}; font-size: 16px; font-weight: 900;")
        settings_btn = QPushButton()
        settings_btn.setIcon(make_gear_icon(16, "#888888"))
        settings_btn.setIconSize(QSize(16, 16))
        settings_btn.setFixedSize(28, 28)
        settings_btn.setStyleSheet(f"background: transparent; border: none;")
        settings_lbl = QLabel("Settings")
        settings_lbl.setStyleSheet(f"color: {SUB}; font-size: 10px; font-family: 'Helvetica Neue'; font-weight: bold;")

        # Traffic lights + auth + settings all on one row
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 10, 0, 0)
        top_row.setSpacing(6)
        def _make_launcher_dot(color, action):
            btn = QPushButton()
            btn.setFixedSize(12, 12)
            btn.setStyleSheet("background: " + color + "; border-radius: 6px; border: none;")
            btn.clicked.connect(action)
            return btn
        top_row.addWidget(_make_launcher_dot("#ff5f57", self.close))
        top_row.addWidget(_make_launcher_dot("#febc2e", self.showMinimized))
        top_row.addWidget(_make_launcher_dot("#28c840", lambda: None))
        top_row.addSpacing(10)

        # Auth avatar + label
        self._auth_avatar = QLabel()
        self._auth_avatar.setFixedSize(16, 16)
        self._auth_avatar.setStyleSheet("background: #444444; border-radius: 8px;")
        self._auth_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        def _draw_anon():
            pix = QPixmap(32, 32)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QColor("#555555"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(0, 0, 32, 32)
            p.setBrush(QColor("#999999"))
            p.drawEllipse(10, 5, 12, 12)
            p.drawEllipse(4, 20, 24, 16)
            p.end()
            pix.setDevicePixelRatio(2.0)
            return pix
        self._auth_avatar.setPixmap(_draw_anon())
        self._auth_label = QLabel("Sign In")
        self._auth_label.setStyleSheet("color: #4a9eff; font-size: 9px; font-weight: bold; background: transparent;")
        self._auth_label.setCursor(Qt.CursorShape.PointingHandCursor)
        top_row.addWidget(self._auth_avatar)
        top_row.addWidget(self._auth_label)
        top_row.addStretch()
        top_row.addWidget(settings_btn)
        top_row.addWidget(settings_lbl)
        layout.addLayout(top_row)

        # Check auth status
        self._auth_worker = YTAuthWorker()
        self._auth_worker.done.connect(self._on_auth_check)
        self._auth_worker.start()

        # Logo + title
        title_row = QHBoxLayout()
        title_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_row.addWidget(logo_lbl)
        title_row.addSpacing(8)
        title_row.addWidget(title)
        layout.addLayout(title_row)

        # Tagline
        tagline = QLabel("Your After Effects YouTube Downloader")
        tagline.setStyleSheet(f"color: {SUB}; font-size: 10px;")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tagline)
        layout.addSpacing(20)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("e.g. youtube.com/c/... or search term")
        self.search_input.setStyleSheet("background: #ffffff; color: #000000; border: none; border-radius: 4px; padding: 6px 10px; font-size: 13px;")
        self.search_input.returnPressed.connect(self._go)
        self.search_input.textChanged.connect(self._on_search_type)
        layout.addWidget(self.search_input)

        # Suggestions dropdown - use popup window so it doesn't get clipped
        self.suggestions_widget = QWidget(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.suggestions_widget.setStyleSheet("background: #111111; border-radius: 6px;")
        self.suggestions_widget.setVisible(False)
        sug_layout = QVBoxLayout(self.suggestions_widget)
        sug_layout.setContentsMargins(6, 6, 6, 6)
        sug_layout.setSpacing(4)
        self._sug_worker = None

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        lbl2 = QLabel("Max Results:")
        lbl2.setStyleSheet(f"color: {SUB};")
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(5, 50)
        self.limit_spin.setValue(10)
        self.limit_spin.setStyleSheet(f"background: {DARK}; color: {FG}; border: none; padding: 4px 8px;")
        self.limit_spin.setFixedWidth(80)
        self.limit_spin.lineEdit().setReadOnly(True)
        bottom.addWidget(lbl2)
        bottom.addWidget(self.limit_spin)
        bottom.addStretch()
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(f"color: {SUB}; font-size: 9px;")
        bottom.addWidget(self.status_lbl)
        self.go_btn = QPushButton("SEARCH \u2192")
        self.go_btn.setObjectName("search_btn")
        self.go_btn.setStyleSheet("background: #f5e642; color: #111111; font-weight: bold; font-size: 12px; padding: 7px 20px; border: none; border-radius: 3px;")
        self.go_btn.clicked.connect(self._go)
        bottom.addWidget(self.go_btn)
        layout.addLayout(bottom)

        bm_lbl = QLabel("BOOKMARKS")
        bm_lbl.setStyleSheet(f"color: {SUB}; font-size: 9px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(bm_lbl)

        self.bm_list = QListWidget()
        self.bm_list.setFixedHeight(144)
        self.bm_list.setStyleSheet(f"""
            QListWidget {{ background: {CARD}; border: none; border-radius: 6px; }}
            QListWidget::item {{ padding: 6px 8px; border-radius: 4px; color: {FG}; }}
            QListWidget::item:hover {{ background: #252525; }}
            QListWidget::item:selected {{ background: {ACC}; color: white; }}
        """)
        self.bm_list.itemDoubleClicked.connect(self._on_bookmark_click)
        self.bm_list.itemClicked.connect(self._on_bookmark_select)
        self.bm_list.itemEntered.connect(self._on_bookmark_hover)
        self.bm_list.setMouseTracking(True)
        self.bm_list.leaveEvent = lambda e: self.search_input.setPlaceholderText("e.g. youtube.com/c/... or search term")
        self.bm_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bm_list.customContextMenuRequested.connect(self._bm_context_menu)
        layout.addWidget(self.bm_list)
        self._refresh_bookmarks()

        loading_page = QWidget()
        loading_page.setStyleSheet(f"background: {GREY};")
        ll = QVBoxLayout(loading_page)
        ll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.setSpacing(10)
        la = QLabel()
        logo2 = make_logo(48)
        if logo2:
            la.setPixmap(logo2)
        else:
            la.setText("\u25b6")
            la.setStyleSheet(f"color: {ACC}; font-size: 32px; font-weight: bold;")
        la.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lt = QLabel("Loading...")
        lt.setStyleSheet(f"color: {FG}; font-size: 13px; font-weight: bold;")
        lt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(la)
        ll.addWidget(lt)

        self.stack.addWidget(search_page)
        self.stack.addWidget(loading_page)
        self.stack.setCurrentIndex(0)
        self.search_input.setFocus()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if hasattr(self, "_drag_pos") and self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def _on_auth_check(self, info):
        if info.get("signed_in"):
            self._auth_label.setText("Log Out")
            self._auth_label.setStyleSheet("color: #888888; font-size: 9px; background: transparent;")
            avatar_url = info.get("avatar", "")
            if avatar_url:
                class _AvatarW(QThread):
                    done = pyqtSignal(QPixmap)
                    def __init__(self, url):
                        super().__init__()
                        self.url = url
                    def run(self):
                        try:
                            import urllib.request
                            with urllib.request.urlopen(self.url, timeout=8) as r:
                                data = r.read()
                            img = QImage()
                            img.loadFromData(data)
                            self.done.emit(QPixmap.fromImage(img))
                        except: pass
                def _set_auth_avatar(pix):
                    screen = QApplication.primaryScreen()
                    ratio = screen.devicePixelRatio() if screen else 2.0
                    size = int(22 * ratio)
                    scaled = pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    x = (scaled.width() - size) // 2
                    y = (scaled.height() - size) // 2
                    scaled = scaled.copy(x, y, size, size)
                    circle = QPixmap(size, size)
                    circle.fill(Qt.GlobalColor.transparent)
                    p = QPainter(circle)
                    p.setRenderHint(QPainter.RenderHint.Antialiasing)
                    path = QPainterPath()
                    path.addEllipse(0, 0, size, size)
                    p.setClipPath(path)
                    p.drawPixmap(0, 0, scaled)
                    p.end()
                    circle.setDevicePixelRatio(ratio)
                    self._auth_avatar.setPixmap(circle)
                self._auth_aw = _AvatarW(avatar_url)
                self._auth_aw.done.connect(_set_auth_avatar)
                self._auth_aw.start()
        else:
            self._auth_label.setText("Sign In")
            self._auth_label.setStyleSheet("color: #4a9eff; font-size: 9px; font-weight: bold; background: transparent;")

    def _refresh_bookmarks(self):
        self.bm_list.clear()
        bookmarks = load_bookmarks()
        if not bookmarks:
            item = QListWidgetItem("  No bookmarks yet \u2014 save a search or channel")
            item.setForeground(QColor(SUB))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.bm_list.addItem(item)
            return
        for bm in bookmarks:
            is_channel = bm.get("type") == "channel"
            item = QListWidgetItem(f"  {bm['name']}" if is_channel else f"  🔍  {bm['name']}")
            item.setData(Qt.ItemDataRole.UserRole, bm["query"])
            item.setFont(QFont("Helvetica Neue", 10))
            if is_channel and bm.get("avatar"):
                pix = load_pixmap(bm["avatar"], 28, 28)
                if pix:
                    circle = QPixmap(28, 28)
                    circle.fill(Qt.GlobalColor.transparent)
                    p = QPainter(circle)
                    p.setRenderHint(QPainter.RenderHint.Antialiasing)
                    cpath = QPainterPath()
                    cpath.addEllipse(0, 0, 28, 28)
                    p.setClipPath(cpath)
                    p.drawPixmap(0, 0, pix)
                    p.end()
                    item.setIcon(QIcon(circle))
            self.bm_list.addItem(item)

    def _on_bookmark_select(self, item):
        query = item.data(Qt.ItemDataRole.UserRole)
        if not query: return
        self.search_input.setText(query)
        self.search_input.setPlaceholderText("e.g. youtube.com/c/... or search term")

    def _on_bookmark_hover(self, item):
        query = item.data(Qt.ItemDataRole.UserRole)
        if query:
            self.search_input.setPlaceholderText(query)
        else:
            self.search_input.setPlaceholderText("e.g. youtube.com/c/... or search term")

    def _on_bookmark_click(self, item):
        query = item.data(Qt.ItemDataRole.UserRole)
        if not query: return
        self.search_input.setText(query)
        self.search_input.setPlaceholderText("e.g. youtube.com/c/... or search term")
        self._go()

    def _bm_context_menu(self, pos):
        item = self.bm_list.itemAt(pos)
        if not item or not item.data(Qt.ItemDataRole.UserRole): return
        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ background: {DARK}; color: {FG}; border: none; border-radius: 4px; padding: 4px; font-size: 11px; }} QMenu::item {{ padding: 6px 16px; }} QMenu::item:selected {{ background: {ACC}; color: white; }}")
        open_action = menu.addAction("Open")
        remove_action = menu.addAction("Remove")
        action = menu.exec(self.bm_list.mapToGlobal(pos))
        if action == open_action:
            self._on_bookmark_click(item)
        elif action == remove_action:
            query = item.data(Qt.ItemDataRole.UserRole)
            bookmarks = [b for b in load_bookmarks() if b["query"] != query]
            save_bookmarks(bookmarks)
            self._refresh_bookmarks()

    def add_bookmark(self, query, name, bm_type="search", avatar=None):
        bookmarks = load_bookmarks()
        for bm in bookmarks:
            if bm["query"] == query: return
        bookmarks.insert(0, {"query": query, "name": name, "type": bm_type, "avatar": avatar})
        bookmarks = bookmarks[:10]
        save_bookmarks(bookmarks)
        self._refresh_bookmarks()

    def _on_search_type(self, text):
        text = text.strip()
        if len(text) < 2 or "youtube.com" in text or "youtu.be" in text or text.startswith("http"):
            self.suggestions_widget.setVisible(False)
            if self._sug_worker and self._sug_worker.isRunning():
                self._sug_worker.terminate()
            return
        if self._sug_worker and self._sug_worker.isRunning():
            self._sug_worker.terminate()
        self._sug_worker = ChannelSuggestWorker(text)
        self._sug_worker.results.connect(self._show_suggestions)
        self._sug_worker.start()

    def _show_suggestions(self, videos):
        if not self.isVisible():
            return
        # Clear old suggestions
        layout = self.suggestions_widget.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not videos:
            self.suggestions_widget.setVisible(False)
            return
        added = 0
        for v in videos:
            channel = v.get("name", "")
            if not channel: continue
            thumb_url = v.get("avatar", "")
            channel_url = v.get("url", "")
            subs = v.get("subs", 0)
            if subs >= 1_000_000: sub_str = f"{subs/1_000_000:.1f}M"
            elif subs >= 1_000: sub_str = f"{subs//1_000}K"
            else: sub_str = ""

            row = QWidget()
            row.setFixedHeight(52)
            row.setStyleSheet("background: transparent; border-radius: 6px;")
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(10, 6, 10, 6)
            rl.setSpacing(12)

            # Circular avatar
            thumb_lbl = QLabel()
            thumb_lbl.setFixedSize(36, 36)
            thumb_lbl.setStyleSheet("background: #333333; border-radius: 18px;")
            thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb_lbl.setScaledContents(False)
            rl.addWidget(thumb_lbl)

            # Channel name + subs
            text_col = QVBoxLayout()
            text_col.setSpacing(1)
            name_lbl = QLabel(channel)
            name_lbl.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: bold; background: transparent;")
            sub_lbl = QLabel(sub_str + " subscribers" if sub_str else "")
            sub_lbl.setStyleSheet("color: #888888; font-size: 9px; background: transparent;")
            text_col.addWidget(name_lbl)
            text_col.addWidget(sub_lbl)
            rl.addLayout(text_col, stretch=1)

            # Load circular avatar
            if thumb_url:
                def _set_thumb(idx, pix, lbl=thumb_lbl):
                    screen = QApplication.primaryScreen()
                    ratio = screen.devicePixelRatio() if screen else 2.0
                    size = 36
                    phys = int(size * ratio)
                    src = pix.scaled(phys, phys, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    x_off = (src.width() - phys) // 2
                    y_off = (src.height() - phys) // 2
                    src = src.copy(x_off, y_off, phys, phys)
                    circle = QPixmap(phys, phys)
                    circle.fill(Qt.GlobalColor.transparent)
                    p = QPainter(circle)
                    p.setRenderHint(QPainter.RenderHint.Antialiasing)
                    cpath = QPainterPath()
                    cpath.addEllipse(0, 0, phys, phys)
                    p.setClipPath(cpath)
                    p.drawPixmap(0, 0, src)
                    p.end()
                    circle.setDevicePixelRatio(ratio)
                    lbl.setFixedSize(size, size)
                    lbl.setPixmap(circle)
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                class _AvatarWorker(QThread):
                    done = pyqtSignal(QPixmap)
                    def __init__(self, url):
                        super().__init__()
                        self.url = url
                    def run(self):
                        try:
                            import urllib.request
                            with urllib.request.urlopen(self.url, timeout=8) as r:
                                data = r.read()
                            img = QImage()
                            img.loadFromData(data)
                            pix = QPixmap.fromImage(img)
                            if not pix.isNull():
                                self.done.emit(pix)
                        except: pass
                _aw = _AvatarWorker(thumb_url)
                _aw.done.connect(lambda pix, lbl=thumb_lbl: _set_thumb(0, pix, lbl))
                _aw.start()
                if not hasattr(self, '_avatar_workers'): self._avatar_workers = []
                self._avatar_workers.append(_aw)

            def _on_click(e, url=channel_url, ch=channel):
                self.search_input.setText(url or ch)
                self.suggestions_widget.setVisible(False)
            row.mousePressEvent = _on_click
            row.enterEvent = lambda e, r=row: r.setStyleSheet("background: #ff0000; border-radius: 6px;")
            row.leaveEvent = lambda e, r=row: r.setStyleSheet("background: transparent; border-radius: 6px;")
            layout.addWidget(row)
            added += 1
            if added >= 3: break
        # Position below search input using global coords
        pos = self.search_input.mapToGlobal(self.search_input.rect().bottomLeft())
        self.suggestions_widget.move(pos.x(), pos.y() + 4)
        self.suggestions_widget.setFixedWidth(self.search_input.width())
        self.suggestions_widget.raise_()
        self.suggestions_widget.setVisible(True)

    def _go(self):
        query = self.search_input.text().strip()
        if not query: return
        self.go_btn.setEnabled(False)
        self.status_lbl.setText("")
        self.stack.setCurrentIndex(1)
        self._worker = SearchWorker(query, self.limit_spin.value())
        self._worker.results.connect(self._on_results)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_results(self, videos):
        if not videos:
            self.stack.setCurrentIndex(0)
            self.status_lbl.setText("No results found.")
            self.go_btn.setEnabled(True)
            return
        self._main = MainWindow(self, videos, query=self.search_input.text().strip())
        self._main.show()
        self._main.raise_()
        self.hide()

    def _on_error(self, msg):
        self.stack.setCurrentIndex(0)
        self.status_lbl.setText(f"Error: {msg}")
        self.go_btn.setEnabled(True)

    def reset(self):
        self.search_input.clear()
        self.go_btn.setEnabled(True)
        self.status_lbl.setText("")
        self.show()
        self.stack.setCurrentIndex(0)
        self._refresh_bookmarks()
        self.search_input.setFocus()


class MainWindow(QMainWindow):
    def __init__(self, launcher, videos, query=""):
        super().__init__()
        self.launcher        = launcher
        self.videos          = videos
        self.selected_video  = None
        self._thumb_workers  = []
        self._info_worker    = None
        self._dl_worker      = None
        self._stream_worker  = None
        self._video_duration = 0
        self._tree_videos    = {}
        self._loop_start     = None
        self._initial_seek   = False
        self._search_query   = query

        self.setWindowTitle("AE Loader")
        self.setFixedSize(780, 540)
        self.setStyleSheet(STYLE)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self._build()
        self.no_video_overlay.setVisible(True)
        self.no_video_overlay.raise_()
        self._populate_list()
        from PyQt6.QtGui import QRegion, QPainterPath
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def paintEvent(self, e):
        from PyQt6.QtGui import QPainter
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(BG))
        painter.end()
        super().paintEvent(e)

    def _on_clipboard(self):
        # Grab current video frame from the label
        pix = self.video_label.pixmap()
        if pix is None or pix.isNull():
            return
        num = len(self._clipboard_items) + 1

        # Container card
        card = QWidget()
        card.setFixedSize(80, 46)
        card.setStyleSheet("background: transparent;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        # Thumbnail with gradient overlay
        thumb = QLabel(card)
        thumb.setGeometry(0, 0, 80, 46)
        scaled = pix.scaled(80, 46, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        # Rounded
        rounded = QPixmap(80, 46)
        rounded.fill(Qt.GlobalColor.transparent)
        p = QPainter(rounded)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, 80, 46, 6, 6)
        p.setClipPath(path)
        p.drawPixmap(0, 0, scaled)
        # Gradient fade on left edge
        from PyQt6.QtGui import QLinearGradient
        grad = QLinearGradient(0, 0, 20, 0)
        grad.setColorAt(0, QColor(0, 0, 0, 180))
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        from PyQt6.QtGui import QBrush
        p.fillRect(0, 0, 80, 46, QBrush(grad))
        # Number badge
        p.setPen(QColor("#ffffff"))
        p.setFont(QFont("Helvetica Neue", 11, QFont.Weight.Bold))
        p.drawText(6, 0, 20, 46, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, str(num))
        p.end()
        thumb.setPixmap(rounded)

        self._clipboard_items.append(card)
        self.clipboard_strip.layout().addWidget(card)
        self.clipboard_strip.setVisible(True)

    def closeEvent(self, event):
        self.launcher.reset()
        event.accept()

    def _build(self):
        central = QWidget()
        central.setAutoFillBackground(True)
        central.setStyleSheet(f"background: {BG};")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        topbar = QWidget()
        topbar.setStyleSheet(f"background: {BG};")
        topbar.setFixedHeight(44)
        self._drag_pos = None
        def _tb_mouse_press(e):
            if e.button() == Qt.MouseButton.LeftButton:
                self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        def _tb_mouse_move(e):
            if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
                self.move(e.globalPosition().toPoint() - self._drag_pos)
        def _tb_mouse_release(e):
            self._drag_pos = None
        topbar.mousePressEvent = _tb_mouse_press
        topbar.mouseMoveEvent = _tb_mouse_move
        topbar.mouseReleaseEvent = _tb_mouse_release
        tl = QHBoxLayout(topbar)
        tl.setContentsMargins(14, 0, 14, 0)
        tl.setSpacing(10)
        logo_lbl = QLabel()
        logo = make_logo(28)
        if logo:
            logo_lbl.setPixmap(logo)
        else:
            logo_lbl.setText("\u25b6")
            logo_lbl.setStyleSheet(f"color: {ACC}; font-size: 14px; font-weight: bold;")
        logo_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        def _logo_click(e):
            self.media_player.stop()
            self.audio_output.setMuted(True)
            self.close()
        logo_lbl.mousePressEvent = _logo_click

        self.status_lbl = QLabel("")
        self.status_lbl.setVisible(False)
        self.top_search = QLineEdit()
        self.top_search.setPlaceholderText("Search or paste channel URL\u2026")
        self.top_search.setStyleSheet(f"background: #252525; color: {FG}; border: none; border-radius: 3px; padding: 4px 10px; font-size: 11px;")
        self.top_search.setFixedHeight(28)
        self.top_search.returnPressed.connect(self._new_search)

        search_btn = QPushButton("SEARCH")
        search_btn.setFixedHeight(28)
        search_btn.setStyleSheet("background: #f5e642; color: #111111; border: none; border-top-left-radius: 3px; border-bottom-left-radius: 3px; padding: 4px 12px; font-size: 11px; font-weight: bold;")
        search_btn.clicked.connect(self._new_search)

        menu_btn = QPushButton()
        menu_btn.setFixedSize(28, 28)
        menu_btn.setStyleSheet("background: #ff0000; color: #ffffff; border: none; border-top-right-radius: 3px; border-bottom-right-radius: 3px; border-left: 1px solid #cc0000;")
        def _draw_bm_topbar(size=14, color="#111111"):
            pix = QPixmap(size, size)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            from PyQt6.QtGui import QPen, QPolygonF
            from PyQt6.QtCore import QPointF
            pen = QPen(QColor(color), 1.5)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            pts = QPolygonF([
                QPointF(3, 1), QPointF(13, 1), QPointF(13, 15),
                QPointF(8, 11), QPointF(3, 15)
            ])
            p.drawPolygon(pts)
            p.end()
            return QIcon(pix)
        menu_btn.setIcon(_draw_bm_topbar(14, "#ffffff"))
        menu_btn.setIconSize(QSize(14, 14))
        menu_btn.clicked.connect(self._show_search_menu)

        # Traffic lights
        def _make_dot(color, hover, action):
            btn = QPushButton()
            btn.setFixedSize(12, 12)
            btn.setStyleSheet(f"background: {color}; border-radius: 6px; border: none;")
            btn.clicked.connect(action)
            return btn
        close_btn = _make_dot("#ff5f57", "#ff3b30", self.close)
        min_btn = _make_dot("#febc2e", "#ffb800", self.showMinimized)
        max_btn = _make_dot("#28c840", "#24b636", lambda: None)
        tl.addWidget(close_btn)
        tl.addSpacing(6)
        tl.addWidget(min_btn)
        tl.addSpacing(6)
        tl.addWidget(max_btn)
        tl.addSpacing(12)
        tl.addWidget(logo_lbl)
        tl.addSpacing(16)
        # Search bar with magnifying glass icon
        search_container = QWidget()
        search_container.setStyleSheet("background: #252525; border-radius: 3px;")
        search_container.setFixedHeight(28)
        sc_layout = QHBoxLayout(search_container)
        sc_layout.setContentsMargins(8, 0, 0, 0)
        sc_layout.setSpacing(4)
        mag_lbl = QLabel()
        mag_lbl.setStyleSheet("background: transparent;")
        mag_lbl.setFixedSize(14, 14)
        def _draw_mag():
            from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath
            pix = QPixmap(14, 14)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor("#888888"), 1.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(1, 1, 8, 8)
            p.drawLine(8, 8, 13, 13)
            p.end()
            return pix
        mag_lbl.setPixmap(_draw_mag())

        # Dropdown container
        mag_container = QWidget()
        mag_container.setStyleSheet("background: transparent;")
        mag_container.setFixedHeight(22)
        mag_container.setCursor(Qt.CursorShape.PointingHandCursor)
        mag_c_layout = QHBoxLayout(mag_container)
        mag_c_layout.setContentsMargins(6, 0, 4, 0)
        mag_c_layout.setSpacing(3)
        mag_c_layout.addWidget(mag_lbl)
        chev_lbl = QLabel()
        chev_lbl.setFixedSize(10, 14)
        def _draw_small_chev():
            pix = QPixmap(10, 14)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            from PyQt6.QtGui import QPen
            pen = QPen(QColor("#888888"), 1.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.drawLine(2, 5, 5, 8)
            p.drawLine(5, 8, 8, 5)
            p.end()
            return pix
        chev_lbl.setPixmap(_draw_small_chev())
        chev_lbl.setStyleSheet("background: transparent;")
        mag_c_layout.addWidget(chev_lbl)
        self._mag_menu = QMenu(self)
        self._mag_menu.setStyleSheet(
            "QMenu { background: #1a1a1a; color: #e8e8e8; border: none; border-radius: 6px; padding: 4px;"
            " font-family: Helvetica Neue; font-size: 11px; }"
            "QMenu::item { padding: 6px 16px; border-radius: 3px; }"
            "QMenu::item:selected { background: #ff0000; color: white; }"
        )
        def _show_mag_menu(e):
            pos = mag_container.mapToGlobal(mag_container.rect().bottomLeft())
            self._mag_menu.exec(pos)
        mag_container.mousePressEvent = _show_mag_menu
        sc_layout.addWidget(mag_container)

        self.top_search.setStyleSheet("background: transparent; color: #e8e8e8; border: none; padding: 4px 6px; font-size: 11px;")
        sc_layout.addWidget(self.top_search)
        tl.addWidget(search_container, stretch=1)
        tl.addWidget(search_btn)
        tl.addWidget(menu_btn)
        root.addWidget(topbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(0)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter)

        left = QWidget()
        left.setStyleSheet(f"background: {CARD}; border: none;")
        left.setFixedWidth(270)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIconSize(QSize(160, 90))
        self.tree.setWordWrap(True)
        self.tree.setIndentation(0)
        self.tree.itemClicked.connect(self._on_tree_click)
        self.tree.itemExpanded.connect(
            lambda item: item.setText(0, item.text(0).replace("\u25b8", "\u25be")) if not item.parent() else None
        )
        self.tree.itemCollapsed.connect(
            lambda item: item.setText(0, item.text(0).replace("\u25be", "\u25b8")) if not item.parent() else None
        )
        self.tree.setItemDelegate(VideoItemDelegate(self.tree))
        self.tree.setVerticalScrollMode(QTreeWidget.ScrollMode.ScrollPerPixel)
        self.tree.verticalScrollBar().setSingleStep(8)
        self.tree.viewport().setStyleSheet(f"background: {CARD};")
        self.tree.setMinimumHeight(0)
        self.tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        ll.addWidget(self.tree, stretch=1)
        splitter.addWidget(left)
        splitter.setStretchFactor(0, 0)

        right = QWidget()
        right.setStyleSheet("background: #2d2d2d;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        video_area = QWidget()
        video_area.setStyleSheet("background: #2d2d2d; border-radius: 8px;")
        video_area.setAutoFillBackground(True)
        video_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        video_area.setMinimumHeight(300)
        PAD = 12

        video_container = QWidget(video_area)
        video_container.setStyleSheet("background: #2d2d2d; border-radius: 12px;")

        self.video_label = QLabel(video_container)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background: #2d2d2d; border-radius: 12px;")
        self.video_label.setVisible(False)

        self.no_video_overlay = QWidget(video_container)
        self.no_video_overlay.setStyleSheet("background: #2d2d2d; border-radius: 8px;")
        nv_layout = QVBoxLayout(self.no_video_overlay)
        nv_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nv_layout.setSpacing(8)
        nv_logo = QLabel()
        nv_logo_pix = make_logo(48)
        if nv_logo_pix:
            nv_logo.setPixmap(nv_logo_pix)
        else:
            nv_logo.setText("\u25b6")
            nv_logo.setStyleSheet(f"color: {ACC}; font-size: 32px; font-weight: bold;")
        nv_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nv_logo.setStyleSheet("background: transparent;")
        self._nv_text = QLabel("Select a video")
        self._nv_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._nv_text.setStyleSheet(f"color: {FG}; font-size: 13px; font-weight: bold; background: transparent;")
        nv_layout.addWidget(nv_logo)
        nv_layout.addWidget(self._nv_text)

        self.ctrl_overlay = QWidget(video_container)
        self.ctrl_overlay.setStyleSheet("background: transparent;")
        self.ctrl_overlay.setFixedHeight(0)
        self.ctrl_overlay.setVisible(False)

        # Bottom fade gradient overlay
        bottom_fade = QWidget(video_container)
        bottom_fade.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        def _paint_bottom_fade(e):
            from PyQt6.QtGui import QPainter, QLinearGradient, QBrush, QColor
            p = QPainter(bottom_fade)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = bottom_fade.width(), bottom_fade.height()
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0, QColor(10, 10, 10, 0))
            grad.setColorAt(0.4, QColor(10, 10, 10, 80))
            grad.setColorAt(1, QColor(10, 10, 10, 220))
            p.fillRect(0, 0, w, h, QBrush(grad))
            p.end()
        bottom_fade.paintEvent = _paint_bottom_fade

        # corner mask overlay - paints rounded corners over the video
        corner_mask = QWidget(video_container)
        corner_mask.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        corner_mask.raise_()

        def _paint_corners(e):
            from PyQt6.QtGui import QPainter, QPainterPath, QColor
            painter = QPainter(corner_mask)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = corner_mask.width(), corner_mask.height()
            # fill entire widget with bg color
            painter.fillRect(0, 0, w, h, QColor("#2d2d2d"))
            # cut out the rounded rectangle (show video through hole)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            path = QPainterPath()
            path.addRoundedRect(0, 0, w, h, 10, 10)
            painter.fillPath(path, QColor(0, 0, 0, 255))
            painter.end()

        corner_mask.paintEvent = _paint_corners
        corner_mask.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        def _resize_video_area(e):
            aw, ah = e.size().width(), e.size().height()
            max_w = aw - PAD * 2
            max_h = ah - PAD * 2
            vid_w = min(max_w, int(max_h * 16 / 9))
            vid_h = int(vid_w * 9 / 16)
            x = (aw - vid_w) // 2
            y = (ah - vid_h) // 2
            video_container.setGeometry(x, y, vid_w, vid_h)
            self.video_label.setGeometry(0, 0, vid_w, vid_h)
            self.no_video_overlay.setGeometry(0, 0, vid_w, vid_h)
            fade_h = int(vid_h * 0.3)
            bottom_fade.setGeometry(0, vid_h - fade_h, vid_w, fade_h)
            bottom_fade.raise_()
            corner_mask.setGeometry(0, 0, vid_w, vid_h)
            corner_mask.raise_()

        video_area.resizeEvent = _resize_video_area
        rl.addWidget(video_area, stretch=2)

        # Clipboard strip overlay (floats over top of video_area)
        self.clipboard_strip = QWidget(video_area)
        self.clipboard_strip.setVisible(False)
        self.clipboard_strip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.clipboard_strip.setStyleSheet("background: transparent;")
        self._clipboard_items = []

        def _paint_strip(e):
            from PyQt6.QtGui import QPainter, QLinearGradient, QBrush, QColor
            p = QPainter(self.clipboard_strip)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.clipboard_strip.width(), self.clipboard_strip.height()
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0, QColor(10, 10, 10, 240))
            grad.setColorAt(0.5, QColor(10, 10, 10, 140))
            grad.setColorAt(1, QColor(10, 10, 10, 0))
            p.fillRect(0, 0, w, h, QBrush(grad))
            p.end()

        self.clipboard_strip.paintEvent = _paint_strip
        cs_layout = QHBoxLayout(self.clipboard_strip)
        cs_layout.setContentsMargins(8, 8, 8, 8)
        cs_layout.setSpacing(6)
        cs_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Resize strip when video_area resizes
        _orig_resize = video_area.resizeEvent
        def _va_resize(e):
            _orig_resize(e)
            self.clipboard_strip.setGeometry(0, 0, video_area.width(), 70)
            self.clipboard_strip.raise_()
        video_area.resizeEvent = _va_resize

        # Persistent controls bar below video
        ctrl_bar = QWidget()
        ctrl_bar.setStyleSheet(f"background: #1a0000;")
        ctrl_bar.setFixedHeight(34)
        ctrl_bar_layout = QHBoxLayout(ctrl_bar)
        ctrl_bar_layout.setContentsMargins(10, 0, 10, 0)
        ctrl_bar_layout.setSpacing(8)
        self.mute_btn = QPushButton()
        self.mute_btn.setIcon(make_mute_icon(16, True))
        self.mute_btn.setIconSize(QSize(16, 16))
        self.mute_btn.setFixedSize(32, 26)
        self.mute_btn.setStyleSheet(f"background: #333333; border: none; border-radius: 4px;")
        self.mute_btn.clicked.connect(self._toggle_mute)
        self.play_btn = QPushButton()
        self.play_btn.setIcon(make_pause_icon(16))
        self.play_btn.setIconSize(QSize(16, 16))
        self.play_btn.setFixedSize(32, 26)
        self.play_btn.setStyleSheet(f"background: #333333; border: none; border-radius: 4px;")
        self.play_btn.clicked.connect(self._toggle_play)
        ctrl_bar_layout.addWidget(self.mute_btn)
        ctrl_bar_layout.addWidget(self.play_btn)
        self.comment_btn = QPushButton()
        self.comment_btn.setIcon(make_comment_icon(16, "#888888"))
        self.comment_btn.setIconSize(QSize(16, 16))
        self.comment_btn.setFixedSize(32, 26)
        self.comment_btn.setStyleSheet(f"background: #333333; border: none; border-radius: 4px;")
        self.comment_btn.setCheckable(True)
        self.comment_btn.clicked.connect(self._toggle_comments)
        self.mute_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.comment_btn.setEnabled(False)
        self.mute_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.comment_btn.setEnabled(False)
        ctrl_bar_layout.addWidget(self.comment_btn)
        ctrl_bar_layout.addStretch()
        preset_btn = QPushButton()
        preset_btn.setFixedSize(32, 26)
        preset_btn.setStyleSheet(f"background: #333333; border: none; border-radius: 4px;")
        def _draw_bookmark_icon(size=16, color="#888888"):
            pix = QPixmap(size, size)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            from PyQt6.QtGui import QPen, QPolygonF
            from PyQt6.QtCore import QPointF
            pen = QPen(QColor(color), 1.5)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            pts = QPolygonF([
                QPointF(3, 1), QPointF(13, 1), QPointF(13, 15),
                QPointF(8, 11), QPointF(3, 15)
            ])
            p.drawPolygon(pts)
            p.end()
            return QIcon(pix)
        preset_btn.setIcon(_draw_bookmark_icon())
        preset_btn.setIconSize(QSize(16, 16))
        preset_btn.clicked.connect(self._show_preset_menu)
        ctrl_bar_layout.addWidget(preset_btn)
        rl.addWidget(ctrl_bar)

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(1.0)
        self.audio_output.setMuted(True)
        self.video_sink = QVideoSink()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_sink)
        self.video_sink.videoFrameChanged.connect(self._on_video_frame)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.mediaStatusChanged.connect(self._on_media_status)


        # SETTINGS collapsible section
        self._settings_visible = True
        self.settings_header = QWidget()
        self.settings_header.setStyleSheet("background: #252525;")
        self.settings_header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_header.setFixedHeight(24)
        settings_hl = QHBoxLayout(self.settings_header)
        settings_hl.setContentsMargins(10, 0, 10, 0)
        self._settings_arrow = QLabel("\u25be")
        settings_title = QLabel("BASIC")
        settings_title = QLabel("BASIC")
        settings_title.setStyleSheet(f"color: {SUB}; font-size: 9px; font-weight: bold; letter-spacing: 1px;")
        settings_hl.addWidget(self._settings_arrow)
        settings_hl.addSpacing(4)
        settings_hl.addWidget(settings_title)
        settings_hl.addStretch()
        rl.addWidget(self.settings_header)

        self.settings_panel = QWidget()
        self.settings_panel.setStyleSheet(f"background: {GREY};")
        settings_panel_layout = QVBoxLayout(self.settings_panel)
        settings_panel_layout.setContentsMargins(0, 0, 0, 0)
        settings_panel_layout.setSpacing(0)

        def _toggle_settings(e):
            self._settings_visible = not self._settings_visible
            self.settings_panel.setVisible(self._settings_visible)
            self._settings_arrow.setText("\u25be" if self._settings_visible else "\u25b8")
        self.settings_header.mousePressEvent = _toggle_settings

        tr_frame = QWidget()
        tr_frame.setStyleSheet(f"background: {GREY};")
        tr_layout = QHBoxLayout(tr_frame)
        tr_layout.setContentsMargins(10, 5, 10, 5)
        tr_layout.setSpacing(8)
        option_lbl = QLabel("Option:")
        option_lbl.setStyleSheet(f"color: {SUB}; font-size: 10px;")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Timestamps", "Full Video", "Full Video + Timestamps", "Random"])
        self.mode_combo.setFixedWidth(155)
        self.mode_combo.setFrame(False)
        self.mode_combo.setItemDelegate(SimpleComboDelegate(self.mode_combo))
        self.mode_combo.view().window().setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.mode_combo.setStyleSheet("background: #1a1a1a; color: #ffffff; border: none; border-radius: 3px; padding: 4px 8px; font-size: 10px; font-family: 'Helvetica Neue';")
        self.mode_combo.currentIndexChanged.connect(self._toggle_range)
        self.start_lbl = QLabel("Start:")
        self.start_lbl.setStyleSheet(f"color: {SUB}; font-size: 10px;")
        self.start_input = DragTimecode("00:00:00", self)
        self.start_input.setFixedWidth(70)
        self.end_lbl = QLabel("End:")
        self.end_lbl.setStyleSheet(f"color: {SUB}; font-size: 10px;")
        self.end_input = DragTimecode("00:00:00", self)
        self.end_input.setFixedWidth(70)
        tr_layout.addWidget(option_lbl)
        tr_layout.addWidget(self.mode_combo)
        tr_layout.addSpacing(4)
        tr_layout.addWidget(self.start_lbl)
        tr_layout.addWidget(self.start_input)
        tr_layout.addWidget(self.end_lbl)
        tr_layout.addWidget(self.end_input)
        self.loop_chk = QCheckBox("Loop")
        self.loop_chk.setStyleSheet(f"color: {SUB}; font-size: 10px;")
        self.loop_chk.stateChanged.connect(self._on_loop_toggle)
        tr_layout.addWidget(self.loop_chk)
        tr_layout.addStretch()
        settings_panel_layout.addWidget(tr_frame)
        self.start_input.timeChanged.connect(self._on_start_drag)
        self.end_input.timeChanged.connect(self._on_end_drag)
        self._toggle_range()

        bottom = QWidget()
        bottom.setStyleSheet(f"background: {GREY};")
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(10, 5, 10, 5)
        bl.setSpacing(6)

        fmt_lbl = QLabel("Format:")
        fmt_lbl.setStyleSheet(f"color: {SUB}; font-size: 10px;")
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["MP4", "MP3"])
        self.fmt_combo.setFixedWidth(62)
        self.fmt_combo.setFrame(False)
        self.fmt_combo.setItemDelegate(SimpleComboDelegate(self.fmt_combo))
        self.fmt_combo.view().window().setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.fmt_combo.setStyleSheet("background: #1a1a1a; color: #ffffff; border: none; border-radius: 3px; padding: 4px 8px; font-size: 10px; font-family: 'Helvetica Neue';")

        qual_lbl = QLabel("Quality:")
        qual_lbl.setStyleSheet(f"color: {SUB}; font-size: 10px;")
        self.qual_combo = QComboBox()
        self.qual_combo.addItems(["Best", "Good", "Low"])
        self.qual_combo.setFixedWidth(62)
        self.qual_combo.setFrame(False)
        self.qual_combo.setItemDelegate(SimpleComboDelegate(self.qual_combo))
        self.qual_combo.view().window().setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.qual_combo.setStyleSheet("background: #1a1a1a; color: #ffffff; border: none; border-radius: 3px; padding: 4px 8px; font-size: 10px; font-family: 'Helvetica Neue';")

        save_lbl = QLabel("Save:")
        save_lbl.setStyleSheet(f"color: {SUB}; font-size: 10px;")
        self.save_input = QLineEdit(os.path.expanduser("~/Downloads"))
        self.save_input.setStyleSheet("background: #1a1a1a; color: #ffffff; padding: 3px 6px; font-size: 10px;")

        browse_btn = QPushButton("\u2026")
        browse_btn.setFixedWidth(28)
        browse_btn.setStyleSheet(f"background: {DARK}; color: {FG}; border: none; border-radius: 3px; padding: 3px; font-size: 12px;")
        browse_btn.clicked.connect(self._browse)

        import_lbl = QLabel("Import At:")
        import_lbl.setStyleSheet(f"color: {SUB}; font-size: 10px;")
        self.ae_combo = QComboBox()
        self.ae_combo.addItems(["Playhead", "Start", "End"])
        self.ae_combo.setFixedWidth(82)
        self.ae_combo.setFrame(False)
        self.ae_combo.setItemDelegate(SimpleComboDelegate(self.ae_combo))
        self.ae_combo.view().window().setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.ae_combo.setStyleSheet("background: #1a1a1a; color: #ffffff; border: none; border-radius: 3px; padding: 4px 8px; font-size: 10px; font-family: 'Helvetica Neue';")

        bl.addWidget(fmt_lbl)
        bl.addWidget(self.fmt_combo)
        bl.addWidget(qual_lbl)
        bl.addWidget(self.qual_combo)
        bl.addWidget(save_lbl)
        bl.addWidget(self.save_input, stretch=1)
        bl.addWidget(browse_btn)
        bl.addSpacing(4)
        bl.addWidget(import_lbl)
        bl.addWidget(self.ae_combo)
        settings_panel_layout.addWidget(bottom)

        qa_frame = QWidget()
        qa_frame.setStyleSheet(f"background: {GREY};")
        ql = QHBoxLayout(qa_frame)
        ql.setContentsMargins(10, 4, 10, 4)
        ql.setSpacing(8)
        qa_lbl = QLabel("Quick Actions:")
        qa_lbl.setStyleSheet(f"color: {SUB}; font-size: 10px;")
        self.qa_combo = QComboBox()
        self.qa_combo.addItems(["None", "Remove Green Screen", "Remove Black Screen"])
        self.qa_combo.setFixedWidth(160)
        self.qa_combo.setFrame(False)
        self.qa_combo.setItemDelegate(SimpleComboDelegate(self.qa_combo))
        self.qa_combo.view().window().setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.qa_combo.setStyleSheet("background: #1a1a1a; color: #ffffff; border: none; border-radius: 3px; padding: 4px 8px; font-size: 10px; font-family: 'Helvetica Neue';")
        ql.addWidget(qa_lbl)
        ql.addWidget(self.qa_combo)
        ql.addStretch()
        settings_panel_layout.addWidget(qa_frame)
        rl.addWidget(self.settings_panel)

        # ADVANCED collapsible section
        self._adv_visible = False
        self.adv_header = QWidget()
        self.adv_header.setStyleSheet("background: #252525;")
        self.adv_header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.adv_header.setFixedHeight(24)
        adv_hl = QHBoxLayout(self.adv_header)
        adv_hl.setContentsMargins(10, 0, 10, 0)
        self._adv_arrow = QLabel("\u25b8")
        self._adv_arrow.setStyleSheet(f"color: {SUB}; font-size: 9px;")
        adv_title = QLabel("ADVANCED")
        adv_title.setStyleSheet(f"color: {SUB}; font-size: 9px; font-weight: bold; letter-spacing: 1px;")
        adv_hl.addWidget(self._adv_arrow)
        adv_hl.addSpacing(4)
        adv_hl.addWidget(adv_title)
        adv_hl.addStretch()
        rl.addWidget(self.adv_header)

        self.adv_panel = QWidget()
        self.adv_panel.setStyleSheet("background: #252525;")
        self.adv_panel.setVisible(False)
        adv_layout = QHBoxLayout(self.adv_panel)
        adv_layout.setContentsMargins(10, 6, 10, 6)
        adv_layout.setSpacing(6)

        color_lbl = QLabel("Color:")
        color_lbl.setStyleSheet(f"color: {SUB}; font-size: 10px;")
        self.color_combo = QComboBox()
        self.color_combo.setFixedWidth(80)
        self.color_combo.setFrame(False)
        self.color_combo.setStyleSheet("background: #1a1a1a; color: #ffffff; border: none; border-radius: 3px; padding: 2px 4px; font-size: 10px;")
        delegate = ColorLabelDelegate(self.color_combo)
        self.color_combo.setItemDelegate(delegate)

        def _paint_color_combo(e):
            from PyQt6.QtGui import QPainter, QColor
            from PyQt6.QtCore import QRect
            p = QPainter(self.color_combo)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.fillRect(self.color_combo.rect(), QColor("#1a1a1a"))
            color_hex = self.color_combo.currentData()
            swatch_rect = QRect(6, self.color_combo.height()//2 - 6, 12, 12)
            if color_hex:
                p.setBrush(QColor(color_hex))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(swatch_rect, 2, 2)
            else:
                p.setBrush(QColor("#333333"))
                p.setPen(QColor("#555555"))
                p.drawRoundedRect(swatch_rect, 2, 2)
            p.setPen(QColor("#ffffff"))
            text_rect = self.color_combo.rect().adjusted(24, 0, -16, 0)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, self.color_combo.currentText())
            p.end()

        self.color_combo.paintEvent = _paint_color_combo
        for name, hex_color in AE_LABELS:
            self.color_combo.addItem(name)
            idx = self.color_combo.count() - 1
            self.color_combo.setItemData(idx, hex_color, Qt.ItemDataRole.UserRole)

        name_lbl = QLabel("Name:")
        name_lbl.setStyleSheet(f"color: {SUB}; font-size: 10px;")
        self.clip_name_input = QLineEdit()
        self.clip_name_input.setPlaceholderText("Optional name...")
        self.clip_name_input.setStyleSheet("background: #1a1a1a; color: #ffffff; border: none; border-radius: 3px; padding: 3px 6px; font-size: 10px;")
        self.clip_name_input.setFixedHeight(22)
        self.clip_name_input.setFixedWidth(70)

        adv_layout.addWidget(color_lbl)
        adv_layout.addWidget(self.color_combo)
        adv_layout.addWidget(name_lbl)
        adv_layout.addWidget(self.clip_name_input)
        self.source_chk = QCheckBox("Source")
        self.source_chk.setStyleSheet(f"color: {SUB}; font-size: 10px;")
        self.layer_chk = QCheckBox("Layer")
        self.layer_chk.setStyleSheet(f"color: {SUB}; font-size: 10px;")
        adv_layout.addWidget(self.source_chk)
        adv_layout.addWidget(self.layer_chk)
        adv_layout.addStretch()
        rl.addWidget(self.adv_panel)

        def _toggle_adv(e):
            self._adv_visible = not self._adv_visible
            self.adv_panel.setVisible(self._adv_visible)
            self._adv_arrow.setText("\u25be" if self._adv_visible else "\u25b8")
        self.adv_header.mousePressEvent = _toggle_adv

        # Comments panel (hidden by default)
        self.comments_panel = QWidget()
        self.comments_panel.setStyleSheet(f"background: {GREY};")
        self.comments_panel.setVisible(False)
        cp_layout = QVBoxLayout(self.comments_panel)
        cp_layout.setContentsMargins(8, 8, 8, 8)
        cp_layout.setSpacing(0)
        self.comments_list = QListWidget()
        self.comments_list.setStyleSheet(f"""
            QListWidget {{ background: {GREY}; border: none; }}
            QListWidget::item {{ padding: 8px; border-bottom: 1px solid #3a3a3a; color: {FG}; }}
            QListWidget::item:hover {{ background: #333333; }}
            QListWidget::item:selected {{ background: {ACC}; color: white; }}
        """)
        self.comments_list.setWordWrap(True)
        self.comments_list.setItemDelegate(CommentItemDelegate(self.comments_list))
        self.comments_list.itemDoubleClicked.connect(self._on_comment_double_click)
        self._comments_spinner = QLabel("●  ○  ○")
        self._comments_spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._comments_spinner.setStyleSheet(f"color: {SUB}; font-size: 14px; letter-spacing: 4px;")
        self._comments_spin_dots = ["●  ○  ○", "○  ●  ○", "○  ○  ●", "○  ●  ○"]
        self._comments_spin_idx = 0
        self._comments_spin_timer = QTimer()
        self._comments_spin_timer.timeout.connect(self._tick_comment_spinner)
        cp_layout.addWidget(self._comments_spinner)
        cp_layout.addWidget(self.comments_list)
        self.comments_list.setVisible(False)
        rl.addWidget(self.comments_panel, stretch=2)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(2)
        btn_row.setContentsMargins(0, 0, 0, 0)

        self.dl_btn = QPushButton("⬇  DOWNLOAD")
        self.dl_btn.setObjectName("dl_btn")
        self.dl_btn.setFixedHeight(36)
        self.dl_btn.setStyleSheet("background: #f5e642; color: #111111; font-weight: bold; font-size: 13px; border: none; border-radius: 0px;")
        self.dl_btn.clicked.connect(self._download)

        self.clip_btn = QPushButton("CLIPBOARD")
        self.clip_btn.setFixedHeight(36)
        self.clip_btn.setFixedWidth(120)
        self.clip_btn.setStyleSheet("background: #111111; color: #ffffff; font-weight: bold; font-size: 13px; border: none; border-radius: 0px; border-left: 1px solid #333333;")

        btn_row.addWidget(self.dl_btn)
        btn_row.addWidget(self.clip_btn)
        self.clip_btn.clicked.connect(self._on_clipboard)
        rl.addLayout(btn_row)

        self.progress_lbl = QLabel("")
        self.progress_lbl.setStyleSheet(f"color: {SUB}; font-size: 9px; padding: 0px 10px;")
        self.progress_lbl.setFixedHeight(16)
        self.progress_lbl.setWordWrap(True)
        rl.addWidget(self.progress_lbl)

        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)

    def _populate_list(self):
        self.tree.clear()
        self._tree_videos = {}

        # Remove old channel header if exists
        if hasattr(self, "_channel_header") and self._channel_header:
            self._channel_header.setParent(None)
            self._channel_header = None

        # Build channel header from first video info
        v0 = self.videos[0] if self.videos else {}
        channel_name = "Loading..."
        channel_handle = ""
        sub_count = None
        thumb_url = None
        sub_count = v0.get("channel_follower_count")
        sub_str = ""
        video_count = len(self.videos)
        video_str = f"{video_count} videos"

        urls = [(v.get("webpage_url") or v.get("url") or "") for v in self.videos]
        is_channel_url = any(x in self._search_query for x in ["youtube.com/c/", "youtube.com/@", "youtube.com/channel/", "youtube.com/user/"])
        if is_channel_url:
            header = QWidget()
            header.setFixedHeight(110)
            header.setStyleSheet("background: #111111;")
            header_stack = QWidget(header)
            header_stack.setGeometry(0, 0, 270, 110)

            # Blurred background label
            bg_lbl = QLabel(header_stack)
            bg_lbl.setGeometry(0, 0, 270, 110)
            bg_lbl.setStyleSheet("background: #111111;")

            # Overlay to darken
            overlay = QWidget(header_stack)
            overlay.setGeometry(0, 0, 270, 110)
            overlay.setStyleSheet("background: rgba(0,0,0,0.6);")

            # Content on top
            content = QWidget(header_stack)
            content.setGeometry(0, 0, 270, 110)
            content.setStyleSheet("background: transparent;")
            hl = QHBoxLayout(content)
            hl.setContentsMargins(48, 10, 12, 10)
            hl.setSpacing(12)

            # Avatar
            avatar_lbl = QLabel()
            avatar_lbl.setFixedSize(56, 56)
            avatar_lbl.setStyleSheet("border-radius: 28px; background: #333333;")
            hl.addWidget(avatar_lbl)

            # Text + button col
            text_col = QVBoxLayout()
            text_col.setSpacing(1)
            text_col.setContentsMargins(0, 0, 0, 0)
            name_lbl = QLabel(channel_name)
            name_lbl.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold; background: transparent;")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            meta_lbl = QLabel(channel_handle)
            meta_lbl.setStyleSheet(f"color: #aaaaaa; font-size: 8px; background: transparent;")
            meta_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            meta_lbl.setWordWrap(True)

            view_btn = QPushButton("View")
            view_btn.setFixedHeight(22)
            view_btn.setFixedWidth(70)
            view_btn.setStyleSheet(
                "background: #ffffff; color: #111111; border: none; border-radius: 11px;"
                "font-size: 10px; font-weight: bold; font-family: Helvetica Neue;"
            )
            def _show_view_panel(checked, parent=self):
                if hasattr(parent, "_view_overlay") and parent._view_overlay.isVisible():
                    parent._view_overlay.hide()
                    return
                if not hasattr(parent, "_view_overlay"):
                    # Dark overlay covering entire window
                    overlay = QWidget(parent)
                    overlay.setGeometry(0, 0, parent.width(), parent.height())
                    overlay.setStyleSheet("background: rgba(0,0,0,0); border-radius: 10px;")
                    overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

                    def _paint_overlay(e):
                        p = QPainter(overlay)
                        p.fillRect(overlay.rect(), QColor(0, 0, 0, 200))
                        p.end()
                    overlay.paintEvent = _paint_overlay

                    def _overlay_click(e):
                        overlay.hide()
                    overlay.mousePressEvent = _overlay_click

                    # Panel on top of overlay
                    margin = 30
                    panel = QWidget(overlay)
                    panel.setGeometry(margin, margin, parent.width() - margin*2, parent.height() - margin*2)
                    panel.setStyleSheet("background: #1a1a1a; border-radius: 10px;")
                    panel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
                    def _panel_click(e): e.accept()
                    panel.mousePressEvent = _panel_click

                    # Dark red header
                    header = QWidget(panel)
                    header.setGeometry(0, 0, panel.width(), 44)
                    header.setStyleSheet(f"background: {BG}; border-top-left-radius: 10px; border-top-right-radius: 10px;")

                    header_lbl = QLabel("Channel Info", header)
                    header_lbl.setGeometry(0, 0, panel.width(), 44)
                    header_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    header_lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; background: transparent;")

                    parent._view_overlay = overlay

                overlay = parent._view_overlay
                overlay.setGeometry(0, 0, parent.width(), parent.height())
                overlay.raise_()
                overlay.show()
            view_btn.clicked.connect(_show_view_panel)
            text_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text_col.addStretch()
            text_col.addSpacing(8)
            text_col.addWidget(name_lbl)
            text_col.addWidget(meta_lbl)
            text_col.addSpacing(4)
            text_col.addWidget(view_btn)
            text_col.addStretch()
            hl.addLayout(text_col, stretch=1)

            # Insert header above tree
            left_layout = self.tree.parent().layout()
            left_layout.insertWidget(0, header)
            self._channel_header = header

            # Shadow pinned to left panel, just below header, always on top
            left_panel = self.tree.parent()
            shadow = QWidget(left_panel)
            shadow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            shadow.setVisible(False)
            def _paint_shadow(e, w=shadow):
                from PyQt6.QtGui import QPainter, QLinearGradient, QBrush, QColor
                p = QPainter(w)
                grad = QLinearGradient(0, 0, 0, w.height())
                grad.setColorAt(0, QColor(0, 0, 0, 180))
                grad.setColorAt(1, QColor(0, 0, 0, 0))
                p.fillRect(w.rect(), QBrush(grad))
                p.end()
            shadow.paintEvent = _paint_shadow
            def _place_shadow(s=shadow, h=header, lp=left_panel):
                s.setGeometry(0, h.height(), lp.width(), 30)
                s.raise_()
            QTimer.singleShot(200, _place_shadow)
            def _on_scroll(val, s=shadow):
                s.setVisible(val > 10)
                s.raise_()
            self.tree.verticalScrollBar().valueChanged.connect(_on_scroll)

            def _on_channel_info(info, nl=name_lbl, ml=meta_lbl, al=avatar_lbl, bl=bg_lbl, vs=video_str):
                if not info: return
                cn = info.get("name", "")
                ch = info.get("handle", "")
                if ch and not ch.startswith("@"): ch = "@" + ch
                sc = info.get("subs", 0)
                sc_str = ""
                if sc:
                    if sc >= 1_000_000: sc_str = f"{sc/1_000_000:.1f}M subscribers"
                    elif sc >= 1_000: sc_str = f"{sc//1_000}K subscribers"
                    else: sc_str = f"{sc} subscribers"
                if cn: nl.setText(cn)
                ml.setText(ch)
                avatar_url = info.get("avatar", "")
                if not avatar_url: return
                screen = QApplication.primaryScreen()
                ratio = screen.devicePixelRatio() if screen else 2.0
                pix = load_pixmap(avatar_url, 56, 56)
                # Circle avatar - fetch fresh at high res
                import urllib.request
                with urllib.request.urlopen(avatar_url, timeout=8) as resp:
                    raw_data = resp.read()
                from PyQt6.QtGui import QImage
                img = QImage()
                img.loadFromData(raw_data)
                src = QPixmap.fromImage(img)
                size = int(56 * ratio)
                scaled = src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                # Crop to square from center
                x_off = (scaled.width() - size) // 2
                y_off = (scaled.height() - size) // 2
                scaled = scaled.copy(x_off, y_off, size, size)
                circle = QPixmap(size, size)
                circle.fill(Qt.GlobalColor.transparent)
                p = QPainter(circle)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                cpath = QPainterPath()
                cpath.addEllipse(0, 0, size, size)
                p.setClipPath(cpath)
                p.drawPixmap(0, 0, scaled)
                p.end()
                circle.setDevicePixelRatio(ratio)
                al.setPixmap(circle)

                # Blurred bg - use high res source, blur more aggressively
                bg_w, bg_h = int(270 * ratio), int(110 * ratio)
                bg_scaled = src.scaled(bg_w, bg_h, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                bx = (bg_scaled.width() - bg_w) // 2
                by = (bg_scaled.height() - bg_h) // 2
                bg_scaled = bg_scaled.copy(bx, by, bg_w, bg_h)
                # Multi-pass blur
                tmp = bg_scaled.scaled(bg_w//8, bg_h//8, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                tmp = tmp.scaled(bg_w//4, bg_h//4, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                tmp = tmp.scaled(bg_w//2, bg_h//2, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                blurred = tmp.scaled(bg_w, bg_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                # Paint dark overlay
                dp = QPainter(blurred)
                dp.fillRect(blurred.rect(), QColor(0, 0, 0, 170))
                dp.end()
                blurred.setDevicePixelRatio(ratio)
                bl.setPixmap(blurred)

                # Extract dominant colors
                tiny2 = src.scaled(50, 50, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                img2 = tiny2.toImage()
                r1,g1,b1,r2,g2,b2,n = 0,0,0,0,0,0,0
                for xx in range(50):
                    for yy in range(50):
                        c = QColor(img2.pixel(xx, yy))
                        if yy < 25:
                            r1+=c.red(); g1+=c.green(); b1+=c.blue(); n+=1
                        else:
                            r2+=c.red(); g2+=c.green(); b2+=c.blue()
                n = max(n,1)
                c1 = QColor(r1//n, g1//n, b1//n)
                c2 = QColor(r2//n, g2//n, b2//n)
                # Paint gradient directly on a pixmap and set as viewport background
                from PyQt6.QtGui import QLinearGradient, QBrush, QPalette
                self._tree_grad_colors = (c1, c2)
                # Darken colors significantly
                d1 = QColor(c1.red()//3, c1.green()//3, c1.blue()//3)
                d2 = QColor(c2.red()//4, c2.green()//4, c2.blue()//4)
                hex1 = d1.name()
                hex2 = d2.name()
                self.tree.setStyleSheet(
                    f"QTreeWidget {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {hex1}, stop:0.5 {hex2}, stop:1 #111111); border: none; outline: none; }}"
                    f"QTreeWidget::item {{ padding: 3px 4px; border: none; color: #e8e8e8; background: transparent; }}"
                    f"QTreeWidget::item:selected {{ background: #ff0000; color: white; border-radius: 6px; }}"
                    f"QTreeWidget::branch {{ background: transparent; }}"
                )
                self.tree.viewport().setStyleSheet("background: transparent;")

            self._channel_info_worker = ChannelInfoWorker(self._search_query)
            self._channel_info_worker.done.connect(_on_channel_info)
            self._channel_info_worker.start()

            if False:
                def _set_avatar(idx, pix, lbl=avatar_lbl, bg=bg_lbl):
                    screen = QApplication.primaryScreen()
                    ratio = screen.devicePixelRatio() if screen else 2.0

                    # Circular avatar
                    size = int(56 * ratio)
                    scaled = pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    circle = QPixmap(size, size)
                    circle.fill(Qt.GlobalColor.transparent)
                    p = QPainter(circle)
                    p.setRenderHint(QPainter.RenderHint.Antialiasing)
                    cpath = QPainterPath()
                    cpath.addEllipse(0, 0, size, size)
                    p.setClipPath(cpath)
                    p.drawPixmap(0, 0, scaled)
                    p.end()
                    circle.setDevicePixelRatio(ratio)
                    lbl.setPixmap(circle)

                    # Blurred background - scale up and blur
                    bg_w, bg_h = int(270 * ratio), int(110 * ratio)
                    bg_scaled = pix.scaled(bg_w, bg_h, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    # Crop to exact size
                    x_off = (bg_scaled.width() - bg_w) // 2
                    y_off = (bg_scaled.height() - bg_h) // 2
                    bg_scaled = bg_scaled.copy(x_off, y_off, bg_w, bg_h)
                    # Apply blur using QImage
                    from PyQt6.QtGui import QImage
                    import ctypes
                    img = bg_scaled.toImage().convertToFormat(QImage.Format.Format_ARGB32)
                    # Simple box blur
                    from PyQt6.QtGui import QImage
                    blurred = QPixmap(bg_scaled.size())
                    blurred.fill(Qt.GlobalColor.transparent)
                    bp = QPainter(blurred)
                    bp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                    # Draw scaled down then up for blur effect
                    small = bg_scaled.scaled(bg_w//8, bg_h//8, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    bp.drawPixmap(0, 0, small.scaled(bg_w, bg_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    bp.end()
                    blurred.setDevicePixelRatio(ratio)
                    bg.setPixmap(blurred)

                w = ThumbWorker(0, thumb_url)
                w.done.connect(_set_avatar)
                w.start()
                self._thumb_workers.append(w)
        else:
            self._channel_header = None

        videos = [v for v in self.videos if v.get("duration", 0) and v.get("duration", 0) > 60 and not v.get("was_live")]
        shorts = [v for v in self.videos if v.get("duration", 0) and v.get("duration", 0) <= 60]
        lives  = [v for v in self.videos if v.get("was_live") or v.get("live_status") in ("was_live", "is_live")]
        if not videos and not shorts and not lives:
            videos = self.videos

        def add_category(label, vids):
            if not vids: return
            cat = QTreeWidgetItem([f"\u25be {label}  ({len(vids)})"])
            cat.setFont(0, QFont("Helvetica Neue", 9, QFont.Weight.Bold))
            cat.setForeground(0, QColor(SUB))
            cat.setFlags(cat.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            cat.setBackground(0, QColor("#111111"))
            self.tree.addTopLevelItem(cat)
            cat.setExpanded(True)

            for i, v in enumerate(vids):
                title     = v.get("title") or v.get("id", "Unknown")
                dur       = v.get("duration")
                dur_str   = seconds_to_hms(dur) if dur else ""
                views     = v.get("view_count")
                views_str = f"{views:,} views" if views else ""
                meta_parts = [x for x in [views_str, dur_str] if x]
                meta_line  = "  \u00b7  ".join(meta_parts)
                child = QTreeWidgetItem([f"{title}\n{meta_line}"])
                child.setFont(0, QFont("Helvetica Neue", 9, QFont.Weight.Bold))
                cat.addChild(child)
                self._tree_videos[id(child)] = v

                thumb_url = get_thumb_url(v)
                if thumb_url:
                    w = ThumbWorker(i, thumb_url)
                    def _set_icon(idx, pix, c=child):
                        scaled = pix.scaled(160, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        c.setIcon(0, QIcon(scaled))
                    w.done.connect(_set_icon)
                    w.start()
                    self._thumb_workers.append(w)

        add_category("VIDEOS", videos)
        add_category("SHORTS", shorts)
        add_category("LIVE", lives)

        if self.tree.topLevelItemCount() > 0:
            first_cat = self.tree.topLevelItem(0)
            if first_cat.childCount() > 0:
                first_item = first_cat.child(0)
                self.tree.setCurrentItem(first_item)
                self._on_tree_click(first_item, 0)

    def _on_tree_click(self, item, col):
        if not item.parent(): return
        v = self._tree_videos.get(id(item))
        if not v: return
        self._on_select_video(v)

    def _on_select_video(self, v):
        self.selected_video = v
        self.media_player.stop()
        self.no_video_overlay.setVisible(True)
        self.no_video_overlay.raise_()
        self.video_label.setVisible(False)
        self._nv_text.setText("Loading\u2026")
        self.loop_chk.setChecked(False)
        self.ctrl_overlay.hide()
        if self._info_worker and self._info_worker.isRunning():
            self._info_worker.terminate()
        self._info_worker = InfoWorker(v)
        self._info_worker.done.connect(self._show_info)
        self._info_worker.start()

    def _show_info(self, info):
        self.selected_video = info
        self._video_duration = int(info.get("duration") or 0)
        self.start_input.setText("00:00:00")
        self.end_input.setText(seconds_to_hms(min(60, self._video_duration)))
        vid_id = info.get("id", "")
        if vid_id and len(vid_id) == 11:
            self._load_youtube(vid_id)

    def _load_youtube(self, vid_id):
        self._nv_text.setText("Loading preview\u2026")
        self.no_video_overlay.setVisible(True)
        self.no_video_overlay.raise_()
        self.video_label.setVisible(False)
        self.ctrl_overlay.hide()
        self.media_player.stop()
        if self._stream_worker and self._stream_worker.isRunning():
            self._stream_worker.terminate()
        self._stream_worker = StreamWorker(vid_id)
        self._stream_worker.done.connect(self._play_stream)
        self._stream_worker.error.connect(lambda: self._nv_text.setText("Preview unavailable\nYouTube is blocking requests for now. Try again later."))
        self._stream_worker.start()

    def _play_stream(self, stream_url):
        # Clean up previous temp file
        prev = getattr(self, "_preview_tmp", None)
        if prev and os.path.exists(prev) and prev.endswith(".mp4") and "tmp" in prev:
            try: os.unlink(prev)
            except: pass
        self._preview_tmp = stream_url if not stream_url.startswith("http") else None
        self._initial_seek = False
        self.media_player.setSource(QUrl.fromLocalFile(stream_url) if not stream_url.startswith("http") else QUrl(stream_url))
        self.media_player.play()
        QTimer.singleShot(400, self._set_audio)
        self.no_video_overlay.setVisible(False)
        self.video_label.setVisible(True)
        self.video_label.raise_()
        self.ctrl_overlay.show()
        self.ctrl_overlay.raise_()
        self.play_btn.setIcon(make_pause_icon(16))
        self.mute_btn.setIcon(make_mute_icon(16, True))
        self.mute_btn.setEnabled(True)
        self.play_btn.setEnabled(True)
        self.comment_btn.setEnabled(True)

    def _on_media_status(self, status):
        from PyQt6.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.MediaStatus.BufferedMedia and not self._initial_seek:
            self._initial_seek = True
            self.media_player.setPosition(0)
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            current = self.tree.currentItem()
            if not current or not current.parent(): return
            parent = current.parent()
            idx = parent.indexOfChild(current)
            next_item = parent.child(idx + 1)
            if next_item:
                self.tree.setCurrentItem(next_item)
                self._on_tree_click(next_item, 0)
            else:
                cat_idx = self.tree.indexOfTopLevelItem(parent)
                next_cat = self.tree.topLevelItem(cat_idx + 1)
                if next_cat and next_cat.childCount() > 0:
                    first = next_cat.child(0)
                    self.tree.setCurrentItem(first)
                    self._on_tree_click(first, 0)

    def _on_loop_toggle(self, state):
        if state:
            self._loop_start = hms_to_seconds(self.start_input.text())
        else:
            self._loop_start = None

    def _on_position_changed(self, ms):
        mode = self.mode_combo.currentText()
        if mode == "Full Video": return
        secs = ms // 1000
        start_secs = hms_to_seconds(self.start_input.text())
        end_secs = hms_to_seconds(self.end_input.text())
        # If loop is on, use locked start
        if self.loop_chk.isChecked() and self._loop_start is not None:
            if end_secs > self._loop_start and secs >= end_secs:
                self.media_player.setPosition(self._loop_start * 1000)
                self.media_player.play()
        else:
            # Start timecode follows playback
            if secs >= start_secs:
                self.start_input.setText(seconds_to_hms(secs))
                # If start catches end, push end forward by 30s
                if secs >= end_secs:
                    new_end = min(secs + 30, self._video_duration)
                    self.end_input.setText(seconds_to_hms(new_end))

    def _on_video_frame(self, frame):
        if not frame.isValid(): return
        img = frame.toImage()
        if img.isNull(): return
        lw, lh = self.video_label.width(), self.video_label.height()
        if lw <= 0 or lh <= 0: return
        pix = QPixmap.fromImage(img).scaled(lw, lh, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        rounded = QPixmap(pix.size())
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, pix.width(), pix.height(), 12, 12)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pix)
        painter.end()
        self.video_label.setPixmap(rounded)

    def _set_audio(self):
        self.audio_output.setVolume(1.0)
        self.audio_output.setMuted(True)
        self.mute_btn.setIcon(make_mute_icon(16, True))

    def _toggle_mute(self):
        muted = self.audio_output.isMuted()
        self.audio_output.setMuted(not muted)
        self.mute_btn.setIcon(make_mute_icon(16, not muted))

    def _toggle_play(self):
        if self.media_player.isPlaying():
            self.media_player.pause()
            self.play_btn.setIcon(make_play_icon(16))
            self._show_pause_overlay()
        else:
            self.media_player.play()
            self.play_btn.setIcon(make_pause_icon(16))
            self._hide_pause_overlay()

    def _toggle_range(self):
        mode = self.mode_combo.currentText()
        enabled = mode != "Full Video"
        show_loop = mode in ("Timestamps", "Full Video + Timestamps")
        self.start_input.setEnabled(enabled)
        self.end_input.setEnabled(enabled)
        self.start_input.setVisible(enabled)
        self.end_input.setVisible(enabled)
        self.start_lbl.setVisible(enabled)
        self.end_lbl.setVisible(enabled)
        self.loop_chk.setVisible(show_loop)

    def _on_start_drag(self, secs):
        if self._video_duration > 0: secs = min(secs, self._video_duration)
        end_secs = hms_to_seconds(self.end_input.text())
        if secs > end_secs: self.end_input.setText(seconds_to_hms(secs))
        self.start_input.setText(seconds_to_hms(secs))
        self.media_player.setPosition(secs * 1000)

    def _on_end_drag(self, secs):
        if self._video_duration > 0: secs = min(secs, self._video_duration)
        start_secs = hms_to_seconds(self.start_input.text())
        if secs < start_secs: self.start_input.setText(seconds_to_hms(secs))
        self.end_input.setText(seconds_to_hms(secs))
        self.media_player.setPosition(start_secs * 1000)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Save to", self.save_input.text())
        if d: self.save_input.setText(d)

    def _download(self):
        if not self.selected_video: return
        info   = self.selected_video
        vid_id = info.get("id", "")
        url    = (f"https://www.youtube.com/watch?v={vid_id}" if len(vid_id) == 11
                  else info.get("webpage_url") or info.get("url", vid_id))
        out_dir   = self.save_input.text()
        fmt_name  = self.fmt_combo.currentText()
        qual_name = self.qual_combo.currentText()
        mode      = self.mode_combo.currentText()
        if mode == "Random":
            import random
            dur = self._video_duration or 60
            clip_len = random.randint(10, min(60, dur))
            start_s = random.randint(0, max(0, dur - clip_len))
            self.start_input.setText(seconds_to_hms(start_s))
            self.end_input.setText(seconds_to_hms(start_s + clip_len))
        use_range = mode != "Full Video"
        start     = self.start_input.text().strip()
        end       = self.end_input.text().strip()

        if use_range and hms_to_seconds(end) <= hms_to_seconds(start):
            self.progress_lbl.setText("\u26a0 End time must be after start time.")
            return

        if fmt_name == "MP3":
            fmt = "bestaudio/best"
        else:
            if qual_name == "Best":
                fmt = "bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"
            elif qual_name == "Good":
                fmt = "bestvideo[vcodec^=avc1][height<=720]+bestaudio[ext=m4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]"
            else:
                fmt = "bestvideo[vcodec^=avc1][height<=480]+bestaudio[ext=m4a]/bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]"

        self.dl_btn.setEnabled(False)
        self.dl_btn.setText("Downloading…")
        self.progress_lbl.setText("")
        self._hide_pause_overlay()
        self._show_download_overlay()
        clip_name = self.clip_name_input.text().strip()
        self._dl_worker = DownloadWorker(url, out_dir, fmt, not use_range, start, end, is_mp3=(fmt_name == "MP3"), clip_name=clip_name)
        self._dl_worker.progress.connect(self.progress_lbl.setText)
        self._dl_worker.finished.connect(lambda ok, fp: self._on_done(ok, fp))
        self._dl_worker.start()

    def _on_done(self, success, file_path):
        self.dl_btn.setEnabled(True)
        self.dl_btn.setText("⬇  DOWNLOAD")
        self._hide_download_overlay()
        self.media_player.pause()
        self.play_btn.setIcon(make_play_icon(16))
        import threading
        threading.Thread(target=lambda: __import__("subprocess").run(["afplay", "-v", "3", "/System/Library/Sounds/Glass.aiff"]), daemon=True).start()
        if success:
            self.progress_lbl.setText(f"\u2713 Saved to: {self.save_input.text()}")
            QTimer.singleShot(600, lambda: self._show_success_overlay(file_path))
            if file_path and os.path.exists(file_path):
                import_at = self.ae_combo.currentText()
                label_color = self.color_combo.currentData()
                clip_name = self.clip_name_input.text().strip()
                QTimer.singleShot(500, lambda: run_ae_import(file_path, import_at, label_color, clip_name))
        else:
            self.progress_lbl.setText("\u2717 Download failed. Check format/URL.")

    def _new_search(self):
        query = self.top_search.text().strip()
        if not query: return
        self.top_search.setEnabled(False)
        worker = SearchWorker(query, 10)
        worker.results.connect(self._on_new_results)
        worker.error.connect(lambda e: self.top_search.setEnabled(True))
        worker.start()
        self._search_worker = worker

    def _on_new_results(self, videos):
        self.top_search.setEnabled(True)
        self.top_search.clear()
        if not videos: return
        self.videos = videos
        self.tree.clear()
        self._thumb_workers.clear()
        self._populate_list()

    def _show_search_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {DARK}; color: {FG}; border: none; border-radius: 4px; padding: 4px;
                    font-family: "Helvetica Neue"; font-size: 11px; }}
            QMenu::item {{ padding: 6px 16px; border-radius: 3px; }}
            QMenu::item:selected {{ background: {ACC}; color: white; }}
            QMenu::separator {{ height: 1px; background: #333; margin: 4px 8px; }}
        """)
        save_action = menu.addAction("\U0001f516  Save Current Search...")
        menu.addSeparator()
        bookmarks = load_bookmarks()
        bm_actions = {}
        if bookmarks:
            for bm in bookmarks[:8]:
                icon = "\U0001f4fa" if bm.get("type") == "channel" else "\U0001f50d"
                action = menu.addAction(f"{icon}  {bm['name']}")
                bm_actions[action] = bm["query"]
            menu.addSeparator()
            clear_action = menu.addAction("\U0001f5d1  Clear All Bookmarks")
        else:
            no_action = menu.addAction("No bookmarks saved yet")
            no_action.setEnabled(False)
            clear_action = None

        btn = self.sender()
        pos = btn.mapToGlobal(QPoint(0, btn.height()))
        action = menu.exec(pos)
        if action is None:
            return
        if action == save_action:
            self._save_bookmark()
        elif clear_action and action == clear_action:
            save_bookmarks([])
            self.launcher._refresh_bookmarks()
        elif action in bm_actions:
            self.top_search.setText(bm_actions[action])
            self._new_search()

    def _save_bookmark(self):
        query = self.top_search.text().strip()
        if not query and self.selected_video:
            query = self.selected_video.get("channel_url") or self.selected_video.get("uploader_url") or ""
        if not query:
            return
        is_channel = "youtube.com" in query or "youtu.be" in query
        if is_channel:
            self._nv_text.setText("Fetching channel info\u2026")
            info = fetch_channel_info(query)
            name = info["name"] if info else query
            avatar = info["avatar"] if info else None
            self.launcher.add_bookmark(query, name, "channel", avatar)
        else:
            self.launcher.add_bookmark(query, query, "search", None)
        self._nv_text.setText("Bookmark saved!")
        QTimer.singleShot(1500, lambda: self._nv_text.setText(""))

    def _show_preset_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {DARK}; color: {FG}; border: none; border-radius: 4px; padding: 4px;
                    font-family: "Helvetica Neue"; font-size: 11px; }}
            QMenu::item {{ padding: 6px 16px; border-radius: 3px; }}
            QMenu::item:selected {{ background: {ACC}; color: white; }}
            QMenu::separator {{ height: 1px; background: #333; margin: 4px 8px; }}
        """)
        save_action = menu.addAction("\U0001f4be  Save Current Settings...")
        menu.addSeparator()
        presets = load_presets()
        preset_actions = {}
        if presets:
            for p in presets:
                action = menu.addAction(f"  {p['name']}")
                preset_actions[action] = p
            menu.addSeparator()
            clear_action = menu.addAction("\U0001f5d1  Clear All Presets")
        else:
            no_action = menu.addAction("No presets saved yet")
            no_action.setEnabled(False)
            clear_action = None
        btn = self.sender()
        pos = btn.mapToGlobal(QPoint(0, btn.height()))
        action = menu.exec(pos)
        if action is None:
            return
        if action == save_action:
            self._save_preset()
        elif clear_action and action == clear_action:
            save_presets([])
        elif action in preset_actions:
            self._load_preset(preset_actions[action])

    def _save_preset(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if not ok or not name.strip():
            return
        preset = {
            "name": name.strip(),
            "option": self.mode_combo.currentText(),
            "format": self.fmt_combo.currentText(),
            "quality": self.qual_combo.currentText(),
            "save_path": self.save_input.text(),
            "import_at": self.ae_combo.currentText(),
            "quick_action": self.qa_combo.currentText(),
            "color": self.color_combo.currentText(),
            "clip_name": self.clip_name_input.text(),
        }
        presets = load_presets()
        presets = [p for p in presets if p["name"] != name.strip()]
        presets.insert(0, preset)
        save_presets(presets)

    def _load_preset(self, preset):
        combos = {
            "option": self.mode_combo,
            "format": self.fmt_combo,
            "quality": self.qual_combo,
            "import_at": self.ae_combo,
            "quick_action": self.qa_combo,
        }
        for key, combo in combos.items():
            val = preset.get(key, "")
            idx = combo.findText(val)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        if preset.get("save_path"):
            self.save_input.setText(preset["save_path"])
        if preset.get("color"):
            idx = self.color_combo.findText(preset["color"])
            if idx >= 0:
                self.color_combo.setCurrentIndex(idx)
        if preset.get("clip_name") is not None:
            self.clip_name_input.setText(preset["clip_name"])
        # Show advanced panel if color or clip_name is set
        if preset.get("color", "None") != "None" or preset.get("clip_name"):
            self._adv_visible = True
            self.adv_panel.setVisible(True)
            self._adv_arrow.setText("\u25be")
        # Show settings panel
        self._settings_visible = True
        self.settings_panel.setVisible(True)
        self._settings_arrow.setText("\u25be")

    def _show_download_overlay(self):
        if not hasattr(self, "_dl_overlay"):
            self._dl_overlay = QWidget(self.video_label.parent())
            self._dl_overlay.setStyleSheet("background: rgba(0,0,0,180); border-radius: 12px;")
            ov_layout = QVBoxLayout(self._dl_overlay)
            ov_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ov_logo = QLabel()
            logo_pix = make_logo(56)
            if logo_pix:
                ov_logo.setPixmap(logo_pix)
            ov_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ov_logo.setStyleSheet("background: transparent;")
            # Spinning dots label
            self._spin_lbl = QLabel("●  ○  ○")
            self._spin_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._spin_lbl.setStyleSheet("color: white; font-size: 14px; background: transparent; letter-spacing: 4px;")
            self._spin_dots = ["●  ○  ○", "○  ●  ○", "○  ○  ●", "○  ●  ○"]
            self._spin_idx = 0
            self._spin_timer = QTimer()
            self._spin_timer.timeout.connect(self._tick_spinner)
            ov_layout.addWidget(ov_logo)
            ov_layout.addSpacing(8)
            ov_layout.addWidget(self._spin_lbl)
        self._dl_overlay.setGeometry(self.video_label.geometry())
        self._dl_overlay.raise_()
        self._dl_overlay.setVisible(True)
        self._spin_timer.start(250)

    def _tick_spinner(self):
        self._spin_idx = (self._spin_idx + 1) % len(self._spin_dots)
        self._spin_lbl.setText(self._spin_dots[self._spin_idx])

    def _hide_download_overlay(self):
        if hasattr(self, "_dl_overlay"):
            self._spin_timer.stop()
            self._dl_overlay.setVisible(False)

    def _show_pause_overlay(self):
        if hasattr(self, "_dl_overlay") and self._dl_overlay.isVisible(): return
        if not hasattr(self, "_pause_overlay"):
            self._pause_overlay = QWidget(self.video_label.parent())
            self._pause_overlay.setStyleSheet("background: rgba(0,0,0,150); border-radius: 12px;")
            ov_layout = QVBoxLayout(self._pause_overlay)
            ov_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ov_logo = QLabel()
            logo_pix = make_logo(56)
            if logo_pix:
                ov_logo.setPixmap(logo_pix)
            ov_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ov_logo.setStyleSheet("background: transparent;")
            ov_layout.addWidget(ov_logo)
        self._pause_overlay.setGeometry(self.video_label.geometry())
        self._pause_overlay.raise_()
        self._pause_overlay.setVisible(True)

    def _hide_pause_overlay(self):
        if hasattr(self, "_pause_overlay"):
            self._pause_overlay.setVisible(False)

    def _show_success_overlay(self, file_path):
        overlay = QWidget(self)
        overlay.setStyleSheet("background: rgba(0,0,0,180);")
        overlay.setGeometry(0, 0, self.width(), self.height())

        card = QWidget(overlay)
        card.setStyleSheet("background: #1a1a1a; border-radius: 12px;")
        card.setFixedSize(360, 280)
        card.move((overlay.width() - card.width()) // 2, (overlay.height() - card.height()) // 2)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 16, 16, 16)
        cl.setSpacing(10)

        # Video preview
        preview_label = QLabel()
        preview_label.setFixedHeight(160)
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_label.setStyleSheet("background: #000000; border-radius: 8px;")
        cl.addWidget(preview_label)

        msg = QLabel("Successfully downloaded!")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold; background: transparent;")
        cl.addWidget(msg)

        cont_btn = QPushButton("Continue")
        cont_btn.setFixedHeight(32)
        cont_btn.setStyleSheet("background: #f5e642; color: #111111; font-weight: bold; font-size: 11px; border: none; border-radius: 6px;")

        def _close():
            preview_player.stop()
            preview_sink.videoFrameChanged.disconnect()
            overlay.hide()

        cont_btn.clicked.connect(_close)
        cl.addWidget(cont_btn)

        # Setup preview player
        preview_player = QMediaPlayer()
        preview_audio = QAudioOutput()
        preview_audio.setMuted(True)
        preview_sink = QVideoSink()
        preview_player.setAudioOutput(preview_audio)
        preview_player.setVideoOutput(preview_sink)

        def _on_frame(frame):
            if not frame.isValid(): return
            img = frame.toImage()
            if img.isNull(): return
            lw, lh = preview_label.width(), preview_label.height()
            if lw <= 0 or lh <= 0: return
            pix = QPixmap.fromImage(img).scaled(lw, lh, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            rounded = QPixmap(pix.size())
            rounded.fill(Qt.GlobalColor.transparent)
            p = QPainter(rounded)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(0, 0, pix.width(), pix.height(), 8, 8)
            p.setClipPath(path)
            p.drawPixmap(0, 0, pix)
            p.end()
            preview_label.setPixmap(rounded)

        preview_sink.videoFrameChanged.connect(_on_frame)

        if file_path and os.path.exists(file_path):
            preview_player.setSource(QUrl.fromLocalFile(file_path))
            preview_player.play()
            # Loop continuously
            preview_player.setLoops(QMediaPlayer.Loops.Infinite)

        overlay.raise_()
        overlay.show()

    def _toggle_comments(self, checked):
        self.settings_header.setVisible(not checked)
        self.settings_panel.setVisible(not checked and self._settings_visible)
        self.adv_header.setVisible(not checked)
        self.adv_panel.setVisible(not checked and self._adv_visible)
        self.comments_panel.setVisible(checked)
        for w in [self.dl_btn, self.clip_btn, self.progress_lbl]:
            w.setVisible(not checked)
        self.comments_panel.setMinimumHeight(300 if checked else 0)
        if checked:
            self.comment_btn.setIcon(make_comment_icon(16, "#ff0000"))
            self._load_comments()
        else:
            self.comment_btn.setIcon(make_comment_icon(16, "#888888"))

    def _load_comments(self):
        if not self.selected_video: return
        vid_id = self.selected_video.get("id", "")
        if not vid_id: return
        self.comments_list.setVisible(False)
        self._comments_spinner.setVisible(True)
        self._comments_spinner.setText("●  ○  ○")
        self._comments_spin_timer.start(250)
        worker = CommentWorker(vid_id)
        worker.done.connect(self._on_comments_loaded)
        worker.start()
        self._comment_worker = worker

    def _tick_comment_spinner(self):
        self._comments_spin_idx = (self._comments_spin_idx + 1) % len(self._comments_spin_dots)
        self._comments_spinner.setText(self._comments_spin_dots[self._comments_spin_idx])

    def _on_comments_loaded(self, comments):
        self._comments_spin_timer.stop()
        self.comments_list.clear()
        self._comments_spinner.setVisible(False)
        self.comments_list.setVisible(True)
        if not comments:
            self._comments_spinner.setText("No comments found.")
            self._comments_spinner.setVisible(True)
            self.comments_list.setVisible(False)
            return
        for c in comments:
            author = c.get("author", "Unknown")
            text = c.get("text", "")
            likes = c.get("like_count", 0)
            ts = c.get("timestamp", 0)
            if ts:
                import datetime
                dt = datetime.datetime.fromtimestamp(ts)
                now = datetime.datetime.now()
                diff = now - dt
                if diff.days > 365: timestamp = f"{diff.days//365}y ago"
                elif diff.days > 30: timestamp = f"{diff.days//30}mo ago"
                elif diff.days > 0: timestamp = f"{diff.days}d ago"
                elif diff.seconds > 3600: timestamp = f"{diff.seconds//3600}h ago"
                else: timestamp = f"{diff.seconds//60}m ago"
            else:
                timestamp = ""
            # Format like YouTube
            likes_str = f"  {likes:,}" if likes else ""
            display = f"{author}\t{timestamp}\n{text}"
            if likes_str:
                display += f"\n{likes_str}"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, c)
            self.comments_list.addItem(item)

    def _on_comment_double_click(self, item):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {DARK}; color: {FG}; border: none; border-radius: 4px; padding: 4px;
                    font-family: "Helvetica Neue"; font-size: 11px; }}
            QMenu::item {{ padding: 6px 16px; border-radius: 3px; }}
            QMenu::item:selected {{ background: {ACC}; color: white; }}
        """)
        menu.addAction("Import At Playhead")
        menu.exec(self.comments_list.mapToGlobal(self.comments_list.visualItemRect(item).bottomLeft()))

    def _set_status(self, msg):
        self.status_lbl.setText(msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    launcher = Launcher()
    launcher.show()
    sys.exit(app.exec())