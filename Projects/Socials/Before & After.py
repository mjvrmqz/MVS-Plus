#!/usr/bin/env python3
"""
Before & After.py
------------------
Social media video template driven by "Before & After.svg".

What it does:
  1. Reads "Before & After.svg" (must live next to this script, same folder).
  2. Auto-detects the two solid-black placeholder rectangles in the SVG —
     these define where your two video clips go. Because detection is based
     on shape (any path/rect filled pure black), you can redesign the SVG
     freely (new colors, text, decorations, sizes, position) as long as the
     two video "windows" stay solid black, and this script keeps working
     with no code changes.
  3. Prompts you (via native macOS dialogs) to pick 2 video clips.
       - 1st clip picked -> placed in the LEFT-most black rectangle
       - 2nd clip picked -> placed in the RIGHT-most black rectangle
  4. Each clip is scaled + center-cropped to fill its rectangle (cover-fit),
     masked to the rectangle's exact shape (rounded corners etc. preserved),
     and composited UNDER the rest of the SVG artwork so text/borders/
     gradients stay on top like a frame.
  5. Exports a finished MP4 next to the SVG/script.

Requirements (install once):
    pip3 install moviepy cairosvg pillow svgelements numpy

Usage:
    python3 "Before & After.py"

Optional flags:
    --svg PATH        Use a specific SVG instead of auto-finding it next to the script
    --out PATH         Output MP4 path (default: "<svg name> - output.mp4" next to script)
    --scale N           Upscale factor applied to the SVG's native canvas size (default: 4)
    --fps N             Output frame rate (default: 30)
    --duration SECONDS  Force a specific output duration (default: matches the shorter clip)
    --audio left|right|none  Which clip's audio to keep (default: left)
"""

import argparse
import ctypes
import ctypes.util
import os
import platform
import subprocess
import sys
from pathlib import Path


def _fix_macos_cairo_path():
    """On macOS, cairosvg needs the native libcairo library, which is usually
    installed via Homebrew but isn't on the dynamic linker's search path by
    default — especially when running a non-Homebrew Python (conda, etc).
    This finds it automatically so the user never has to set
    DYLD_LIBRARY_PATH or fuss with their shell config by hand."""
    if platform.system() != "Darwin":
        return
    if ctypes.util.find_library("cairo"):
        return  # already discoverable, nothing to do

    candidate_dirs = [
        "/opt/homebrew/lib",       # Apple Silicon Homebrew
        "/usr/local/lib",          # Intel Homebrew
        "/opt/local/lib",          # MacPorts
    ]
    candidate_names = ["libcairo.2.dylib", "libcairo.dylib"]

    for d in candidate_dirs:
        for name in candidate_names:
            full_path = os.path.join(d, name)
            if os.path.exists(full_path):
                # Make it loadable for this process right now...
                try:
                    ctypes.CDLL(full_path)
                except OSError:
                    pass
                # ...and for any child processes / re-exec scenarios.
                os.environ["DYLD_LIBRARY_PATH"] = (
                    d + ":" + os.environ.get("DYLD_LIBRARY_PATH", "")
                )
                os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
                    d + ":" + os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
                )
                return


_fix_macos_cairo_path()

try:
    import numpy as np
    from PIL import Image
    import cairosvg
    from svgelements import SVG, Path as SvgPath, Rect as SvgRect
    from moviepy import VideoFileClip, CompositeVideoClip, ImageClip
except ImportError as e:
    sys.exit(
        "Missing dependency: {}\n\n"
        "Install everything with:\n"
        '  pip3 install moviepy cairosvg pillow svgelements numpy\n'.format(e)
    )

BLACK_FILLS = {"#000000", "#000", "black", "rgb(0,0,0)", "rgb(0, 0, 0)"}


# --------------------------------------------------------------------------
# 1. Locate files
# --------------------------------------------------------------------------

def find_svg(script_dir: Path, override: str | None) -> Path:
    if override:
        p = Path(override).expanduser().resolve()
        if not p.exists():
            sys.exit(f"SVG not found at: {p}")
        return p

    # Prefer an exact-name match, fall back to any .svg in the folder.
    exact = script_dir / "Before & After.svg"
    if exact.exists():
        return exact

    svgs = sorted(script_dir.glob("*.svg"))
    if not svgs:
        sys.exit(
            f"No .svg design found in {script_dir}.\n"
            'Place "Before & After.svg" next to this script, or pass --svg PATH.'
        )
    if len(svgs) > 1:
        print(f"Multiple SVGs found, using: {svgs[0].name}")
    return svgs[0]


# --------------------------------------------------------------------------
# 2. Detect the two black placeholder rectangles in the SVG
# --------------------------------------------------------------------------

class VideoSlot:
    """One black placeholder shape -> one video window."""

    def __init__(self, shape, bbox):
        self.shape = shape  # the svgelements shape object (Path or Rect)
        x0, y0, x1, y1 = bbox
        self.x0, self.y0, self.x1, self.y1 = float(x0), float(y0), float(x1), float(y1)

    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.y1 - self.y0

    def as_svg_fragment(self) -> str:
        """Return a standalone SVG (white shape on black) for mask rendering."""
        d = self.shape.d() if hasattr(self.shape, "d") else None
        if d:
            inner = f'<path d="{d}" fill="white"/>'
        else:
            # Rect fallback
            inner = (
                f'<rect x="{self.shape.x}" y="{self.shape.y}" '
                f'width="{self.shape.width}" height="{self.shape.height}" '
                f'rx="{getattr(self.shape, "rx", 0) or 0}" fill="white"/>'
            )
        return inner


def is_solid_black(fill) -> bool:
    if fill is None:
        return False
    s = str(fill).lower().strip()
    return s in BLACK_FILLS


def detect_video_slots(svg_path: Path):
    svg = SVG.parse(str(svg_path))

    canvas_w = float(svg.width) if svg.width else 0
    canvas_h = float(svg.height) if svg.height else 0
    canvas_area = canvas_w * canvas_h if canvas_w and canvas_h else float("inf")

    found = []
    for el in svg.elements():
        if not isinstance(el, (SvgPath, SvgRect)):
            continue
        if not is_solid_black(getattr(el, "fill", None)):
            continue
        try:
            bbox = el.bbox()
        except Exception:
            continue
        if bbox is None:
            continue
        x0, y0, x1, y1 = bbox
        area = (x1 - x0) * (y1 - y0)
        if area <= 0:
            continue
        # Skip a full-canvas black background (false positive), keep real "windows"
        if canvas_area != float("inf") and area >= canvas_area * 0.9:
            continue
        found.append(VideoSlot(el, bbox))

    if len(found) < 2:
        sys.exit(
            f"Expected 2 solid-black placeholder shapes in {svg_path.name}, "
            f"found {len(found)}.\n"
            "Make sure your two video windows are filled with pure black "
            '(fill="#000000" / fill="black").'
        )
    if len(found) > 2:
        # Keep the two largest — smaller black shapes are probably just text/icons.
        found.sort(key=lambda s: s.width * s.height, reverse=True)
        found = found[:2]

    # Left slot = smaller x0, right slot = larger x0
    found.sort(key=lambda s: s.x0)
    left_slot, right_slot = found[0], found[1]
    return left_slot, right_slot, (canvas_w, canvas_h)


# --------------------------------------------------------------------------
# 3. Mac native "choose file" dialogs
# --------------------------------------------------------------------------

def choose_file_mac(prompt: str) -> Path:
    script = (
        'set theFile to choose file with prompt "{prompt}" '
        'of type {{"public.movie", "public.video", "public.avi", "com.apple.quicktime-movie"}}\n'
        'POSIX path of theFile'
    ).format(prompt=prompt.replace('"', '\\"'))
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        if "User canceled" in (e.stderr or ""):
            sys.exit("Canceled — no file selected.")
        sys.exit(f"Could not open the macOS file picker: {e.stderr.strip()}")
    path = result.stdout.strip()
    if not path:
        sys.exit("No file selected.")
    return Path(path)


# --------------------------------------------------------------------------
# 4. Rendering helpers
# --------------------------------------------------------------------------

def render_svg_to_rgba(svg_path: Path, width: int, height: int) -> np.ndarray:
    png_bytes = cairosvg.svg2png(
        url=str(svg_path), output_width=width, output_height=height
    )
    img = Image.open(__import__("io").BytesIO(png_bytes)).convert("RGBA")
    return np.array(img)


def render_slot_mask(slot: VideoSlot, scale: float, canvas_w: int, canvas_h: int) -> np.ndarray:
    """Render this slot's shape alone as a 0..255 alpha mask at full canvas size."""
    fragment = slot.as_svg_fragment()
    standalone = (
        f'<svg width="{canvas_w}" height="{canvas_h}" '
        f'viewBox="0 0 {canvas_w / scale} {canvas_h / scale}" '
        f'xmlns="http://www.w3.org/2000/svg">{fragment}</svg>'
    )
    png_bytes = cairosvg.svg2png(
        bytestring=standalone.encode("utf-8"),
        output_width=canvas_w, output_height=canvas_h,
    )
    img = Image.open(__import__("io").BytesIO(png_bytes)).convert("RGBA")
    arr = np.array(img)
    # Use alpha channel as the mask (shape drawn, everything else transparent)
    return arr[:, :, 3]


def cover_fit_clip(clip, target_w: int, target_h: int):
    """Resize + center-crop a moviepy clip to exactly fill target_w x target_h."""
    clip_ratio = clip.w / clip.h
    target_ratio = target_w / target_h

    if clip_ratio > target_ratio:
        # Clip is wider than target -> match height, crop sides
        resized = clip.resized(height=target_h)
        excess = resized.w - target_w
        x1 = excess / 2
        resized = resized.cropped(x1=x1, y1=0, x2=x1 + target_w, y2=target_h)
    else:
        # Clip is taller than target -> match width, crop top/bottom
        resized = clip.resized(width=target_w)
        excess = resized.h - target_h
        y1 = excess / 2
        resized = resized.cropped(x1=0, y1=y1, x2=target_w, y2=y1 + target_h)

    return resized


# --------------------------------------------------------------------------
# 5. Main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Before & After social video template")
    parser.add_argument("--svg", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--scale", type=float, default=4.0)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--audio", choices=["left", "right", "none"], default="left")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    svg_path = find_svg(script_dir, args.svg)
    print(f"Using design: {svg_path.name}")

    left_slot, right_slot, (svg_w, svg_h) = detect_video_slots(svg_path)
    print(
        f"Detected LEFT slot:  x[{left_slot.x0:.0f}-{left_slot.x1:.0f}] "
        f"y[{left_slot.y0:.0f}-{left_slot.y1:.0f}]"
    )
    print(
        f"Detected RIGHT slot: x[{right_slot.x0:.0f}-{right_slot.x1:.0f}] "
        f"y[{right_slot.y0:.0f}-{right_slot.y1:.0f}]"
    )

    canvas_w = round(svg_w * args.scale)
    canvas_h = round(svg_h * args.scale)
    scale = args.scale

    # --- Pick clips ---
    print("\nChoose your LEFT clip...")
    left_path = choose_file_mac("Select the LEFT clip")
    print(f"  Left:  {left_path.name}")

    print("Choose your RIGHT clip...")
    right_path = choose_file_mac("Select the RIGHT clip")
    print(f"  Right: {right_path.name}")

    # --- Render the design ---
    print("\nRendering design and masks...")
    full_rgba = render_svg_to_rgba(svg_path, canvas_w, canvas_h)  # the whole artwork
    left_mask = render_slot_mask(left_slot, scale, canvas_w, canvas_h)
    right_mask = render_slot_mask(right_slot, scale, canvas_w, canvas_h)

    # Punch transparent holes into the foreground artwork wherever a video
    # slot's BARE BLACK BACKGROUND shows (i.e. nothing was drawn over it),
    # so the video shows through there. Anything drawn on top of the
    # placeholder in the original design (text, icons, borders, etc.) is
    # left fully intact and stays above the video.
    foreground = full_rgba.copy()
    slot_area = (left_mask > 10) | (right_mask > 10)
    rgb_sum = foreground[:, :, :3].astype("int32").sum(axis=2)
    near_black = rgb_sum < 30  # small tolerance for anti-aliased edges
    hole = slot_area & near_black
    foreground[hole, 3] = 0
    foreground_clip_img = foreground  # RGBA numpy array, used as overlay

    # --- Load + fit clips ---
    print("Loading clips...")
    left_clip_raw = VideoFileClip(str(left_path))
    right_clip_raw = VideoFileClip(str(right_path))

    duration = args.duration or min(left_clip_raw.duration, right_clip_raw.duration)
    left_clip_raw = left_clip_raw.subclipped(0, duration)
    right_clip_raw = right_clip_raw.subclipped(0, duration)

    lx0, ly0 = round(left_slot.x0 * scale), round(left_slot.y0 * scale)
    lw, lh = round(left_slot.width * scale), round(left_slot.height * scale)
    rx0, ry0 = round(right_slot.x0 * scale), round(right_slot.y0 * scale)
    rw, rh = round(right_slot.width * scale), round(right_slot.height * scale)

    left_fitted = cover_fit_clip(left_clip_raw, lw, lh).with_position((lx0, ly0))
    right_fitted = cover_fit_clip(right_clip_raw, rw, rh).with_position((rx0, ry0))

    # Crop each mask to its slot's bounding box and apply as the clip's alpha,
    # so rounded corners / non-rectangular shapes are respected.
    left_mask_crop = (left_mask[ly0:ly0 + lh, lx0:lx0 + lw].astype("float32") / 255.0)
    right_mask_crop = (right_mask[ry0:ry0 + rh, rx0:rx0 + rw].astype("float32") / 255.0)

    left_fitted = left_fitted.with_mask(
        ImageClip(left_mask_crop, is_mask=True).with_duration(duration)
    )
    right_fitted = right_fitted.with_mask(
        ImageClip(right_mask_crop, is_mask=True).with_duration(duration)
    )

    overlay_clip = ImageClip(foreground_clip_img).with_duration(duration)

    # --- Audio selection ---
    if args.audio == "left":
        chosen_audio = left_clip_raw.audio
    elif args.audio == "right":
        chosen_audio = right_clip_raw.audio
    else:
        chosen_audio = None

    # --- Composite: videos first, design overlay (with holes) on top ---
    final = CompositeVideoClip(
        [left_fitted, right_fitted, overlay_clip], size=(canvas_w, canvas_h)
    ).with_duration(duration)

    if chosen_audio is not None:
        final = final.with_audio(chosen_audio)

    # --- Export ---
    out_path = (
        Path(args.out).expanduser().resolve()
        if args.out
        else script_dir / f"{svg_path.stem} - output.mp4"
    )
    print(f"\nExporting to {out_path} ...")
    final.write_videofile(
        str(out_path),
        fps=args.fps,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
    )

    left_clip_raw.close()
    right_clip_raw.close()
    print(f"\nDone! Saved: {out_path}")


if __name__ == "__main__":
    main()
