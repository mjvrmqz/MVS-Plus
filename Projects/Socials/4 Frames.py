#!/usr/bin/env python3
"""
4 Frames.py
------------------
Social media image template driven by "4 Frames.svg".

What it does:
  1. Reads "4 Frames.svg" (must live next to this script, same folder).
  2. Auto-detects the black placeholder area and the cream divider bars that
     split it into a 2x2 grid — top-left, top-right, bottom-left,
     bottom-right. Because detection is based on shape (the solid-black
     backing rect + the cream/light divider bars carving it up), you can
     redesign the SVG freely (new colors, borders, decorations, sizes,
     position) as long as that basic structure holds, and this script keeps
     working with no code changes.
  3. Prompts you (via native macOS dialogs) to pick 4 images.
       - 1st image picked -> placed in the TOP-LEFT frame
       - 2nd image picked -> placed in the TOP-RIGHT frame
       - 3rd image picked -> placed in the BOTTOM-LEFT frame
       - 4th image picked -> placed in the BOTTOM-RIGHT frame
  4. Each image is scaled + center-cropped to fill its frame (cover-fit),
     masked to the frame's exact shape, and composited UNDER the rest of
     the SVG artwork so dividers/borders stay on top like a frame.
  5. Exports a finished 1920x1080 PNG next to the SVG/script, colour-managed
     (sRGB) end to end so on-screen colour matches the source images.

Requirements (install once):
    pip3 install pillow cairosvg svgelements numpy

Usage:
    python3 "4 Frames.py"

Optional flags:
    --svg PATH    Use a specific SVG instead of auto-finding it next to the script
    --out PATH    Output PNG path (default: "<svg name> - output.png" next to script)
    --width N     Output width in pixels (default: 1920)
    --height N    Output height in pixels (default: 1080)
"""

import argparse
import ctypes
import ctypes.util
import io
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
                try:
                    ctypes.CDLL(full_path)
                except OSError:
                    pass
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
    from PIL import Image, ImageCms
    import cairosvg
    from svgelements import SVG, Path as SvgPath, Rect as SvgRect
except ImportError as e:
    sys.exit(
        "Missing dependency: {}\n\n"
        "Install everything with:\n"
        '  pip3 install pillow cairosvg svgelements numpy\n'.format(e)
    )

BLACK_FILLS = {"#000000", "#000", "black", "rgb(0,0,0)", "rgb(0, 0, 0)"}

# The cream/light divider color used in "4 Frames.svg". Kept as a set so a
# slightly different hex (light re-theme) still gets recognized, but the
# real detection below is shape/position based, not color based, so a
# totally different divider color still works automatically.
DIVIDER_HINT_FILLS = {"#f6ebca"}


# --------------------------------------------------------------------------
# 1. Locate files
# --------------------------------------------------------------------------

def find_svg(script_dir: Path, override):
    if override:
        p = Path(override).expanduser().resolve()
        if not p.exists():
            sys.exit(f"SVG not found at: {p}")
        return p

    exact = script_dir / "4 Frames.svg"
    if exact.exists():
        return exact

    svgs = sorted(script_dir.glob("*.svg"))
    if not svgs:
        sys.exit(
            f"No .svg design found in {script_dir}.\n"
            'Place "4 Frames.svg" next to this script, or pass --svg PATH.'
        )
    if len(svgs) > 1:
        print(f"Multiple SVGs found, using: {svgs[0].name}")
    return svgs[0]


# --------------------------------------------------------------------------
# 2. Detect the 2x2 grid of image placeholders in the SVG
# --------------------------------------------------------------------------

class ImageSlot:
    """One quadrant of the black placeholder area -> one image window."""

    def __init__(self, x0, y0, x1, y1, label):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.label = label

    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.y1 - self.y0

    def as_svg_fragment(self) -> str:
        return f'<rect x="{self.x0}" y="{self.y0}" width="{self.width}" height="{self.height}" fill="white"/>'


def is_solid_black(fill) -> bool:
    if fill is None:
        return False
    s = str(fill).lower().strip()
    return s in BLACK_FILLS


def detect_grid(svg_path: Path):
    """Find the big black backing rect, then use any non-black shapes that
    overlap it (the cream divider bars) to carve it into a 2x2 grid of four
    equal-ish quadrants: top-left, top-right, bottom-left, bottom-right."""
    svg = SVG.parse(str(svg_path))

    canvas_w = float(svg.width) if svg.width else 0
    canvas_h = float(svg.height) if svg.height else 0

    black_shapes = []
    divider_bboxes = []

    for el in svg.elements():
        if not isinstance(el, (SvgPath, SvgRect)):
            continue
        fill = getattr(el, "fill", None)
        try:
            bbox = el.bbox()
        except Exception:
            continue
        if bbox is None:
            continue
        x0, y0, x1, y1 = (float(v) for v in bbox)
        area = (x1 - x0) * (y1 - y0)
        if area <= 0:
            continue

        if is_solid_black(fill):
            black_shapes.append((x0, y0, x1, y1, area))
        else:
            divider_bboxes.append((x0, y0, x1, y1))

    if not black_shapes:
        sys.exit(
            f"No solid-black placeholder area found in {svg_path.name}.\n"
            'Make sure the 4-frame backing area is filled with pure black '
            '(fill="#000000" / fill="black").'
        )

    # Largest black shape is the backing area that gets divided into 4.
    black_shapes.sort(key=lambda s: s[4], reverse=True)
    bx0, by0, bx1, by1, _ = black_shapes[0]

    # Find the vertical divider (tall, narrow, spans ~full height, sits
    # roughly in the horizontal middle) and horizontal divider (wide, short,
    # spans ~full width, sits roughly in the vertical middle) among the
    # non-black shapes that overlap the backing rect.
    v_divider = None
    h_divider = None
    for (dx0, dy0, dx1, dy1) in divider_bboxes:
        # must overlap the backing rect to be relevant
        if dx1 <= bx0 or dx0 >= bx1 or dy1 <= by0 or dy0 >= by1:
            continue
        dw, dh = dx1 - dx0, dy1 - dy0
        if dh >= (by1 - by0) * 0.9 and dw < dh:
            v_divider = (dx0, dy0, dx1, dy1)
        elif dw >= (bx1 - bx0) * 0.9 and dh < dw:
            h_divider = (dx0, dy0, dx1, dy1)

    # Midpoints: prefer the divider bar's own center, fall back to the
    # geometric center of the backing rect if a divider wasn't found (still
    # produces a clean even split).
    mid_x = (v_divider[0] + v_divider[2]) / 2 if v_divider else (bx0 + bx1) / 2
    mid_y = (h_divider[1] + h_divider[3]) / 2 if h_divider else (by0 + by1) / 2

    # Gaps: half the divider thickness on each side, so frames don't overlap
    # the divider bar itself.
    gap_x = ((v_divider[2] - v_divider[0]) / 2) if v_divider else 0
    gap_y = ((h_divider[3] - h_divider[1]) / 2) if h_divider else 0

    top_left = ImageSlot(bx0, by0, mid_x - gap_x, mid_y - gap_y, "top-left")
    top_right = ImageSlot(mid_x + gap_x, by0, bx1, mid_y - gap_y, "top-right")
    bottom_left = ImageSlot(bx0, mid_y + gap_y, mid_x - gap_x, by1, "bottom-left")
    bottom_right = ImageSlot(mid_x + gap_x, mid_y + gap_y, bx1, by1, "bottom-right")

    return top_left, top_right, bottom_left, bottom_right, (canvas_w, canvas_h)


# --------------------------------------------------------------------------
# 3. Mac native "choose file" dialogs
# --------------------------------------------------------------------------

def choose_file_mac(prompt: str) -> Path:
    script = (
        'set theFile to choose file with prompt "{prompt}" '
        'of type {{"public.image", "public.jpeg", "public.png", "public.heic", "public.tiff"}}\n'
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
# 4. Rendering / color-accurate image helpers
# --------------------------------------------------------------------------

SRGB_PROFILE = None


def _get_srgb_profile():
    global SRGB_PROFILE
    if SRGB_PROFILE is None:
        SRGB_PROFILE = ImageCms.createProfile("sRGB")
    return SRGB_PROFILE


def load_image_srgb(path: Path) -> Image.Image:
    """Open an image and normalize it to sRGB so colors match what the
    source file looks like, regardless of any embedded color profile
    (wide-gamut camera JPEGs, HEICs, etc)."""
    img = Image.open(path)
    img = ImageCms.exif_transpose(img) if hasattr(ImageCms, "exif_transpose") else img
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    icc = img.info.get("icc_profile")
    if icc:
        try:
            src_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            img = ImageCms.profileToProfile(
                img.convert("RGBA") if img.mode != "RGBA" else img,
                src_profile,
                _get_srgb_profile(),
                outputMode="RGBA",
            )
        except Exception:
            img = img.convert("RGBA")
    else:
        img = img.convert("RGBA")
    return img


def render_svg_to_rgba(svg_path: Path, width: int, height: int) -> np.ndarray:
    png_bytes = cairosvg.svg2png(
        url=str(svg_path), output_width=width, output_height=height
    )
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    return np.array(img)


def render_slot_mask(slot: ImageSlot, canvas_w: int, canvas_h: int, svg_w: float, svg_h: float) -> np.ndarray:
    """Render this slot's rectangle alone as a 0..255 alpha mask at full
    output canvas size."""
    fragment = slot.as_svg_fragment()
    standalone = (
        f'<svg width="{canvas_w}" height="{canvas_h}" '
        f'viewBox="0 0 {svg_w} {svg_h}" '
        f'xmlns="http://www.w3.org/2000/svg">{fragment}</svg>'
    )
    png_bytes = cairosvg.svg2png(
        bytestring=standalone.encode("utf-8"),
        output_width=canvas_w, output_height=canvas_h,
    )
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    arr = np.array(img)
    return arr[:, :, 3]


def cover_fit_image(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize + center-crop a PIL image to exactly fill target_w x target_h
    (cover-fit), using a high quality resampler."""
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        new_h = target_h
        new_w = round(new_h * src_ratio)
    else:
        new_w = target_w
        new_h = round(new_w / src_ratio)

    resized = img.resize((new_w, new_h), Image.LANCZOS)
    x0 = round((new_w - target_w) / 2)
    y0 = round((new_h - target_h) / 2)
    return resized.crop((x0, y0, x0 + target_w, y0 + target_h))


# --------------------------------------------------------------------------
# 5. Main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="4 Frames social image template")
    parser.add_argument("--svg", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    svg_path = find_svg(script_dir, args.svg)
    print(f"Using design: {svg_path.name}")

    tl, tr, bl, br, (svg_w, svg_h) = detect_grid(svg_path)
    for slot in (tl, tr, bl, br):
        print(
            f"Detected {slot.label:<12} x[{slot.x0:.0f}-{slot.x1:.0f}] "
            f"y[{slot.y0:.0f}-{slot.y1:.0f}]"
        )

    canvas_w, canvas_h = args.width, args.height

    # --- Pick images ---
    print("\nChoose your TOP-LEFT image...")
    tl_path = choose_file_mac("Select the TOP-LEFT image")
    print(f"  Top-left:     {tl_path.name}")

    print("Choose your TOP-RIGHT image...")
    tr_path = choose_file_mac("Select the TOP-RIGHT image")
    print(f"  Top-right:    {tr_path.name}")

    print("Choose your BOTTOM-LEFT image...")
    bl_path = choose_file_mac("Select the BOTTOM-LEFT image")
    print(f"  Bottom-left:  {bl_path.name}")

    print("Choose your BOTTOM-RIGHT image...")
    br_path = choose_file_mac("Select the BOTTOM-RIGHT image")
    print(f"  Bottom-right: {br_path.name}")

    # --- Render the design ---
    print("\nRendering design and masks...")
    full_rgba = render_svg_to_rgba(svg_path, canvas_w, canvas_h)  # the whole artwork
    masks = {
        slot.label: render_slot_mask(slot, canvas_w, canvas_h, svg_w, svg_h)
        for slot in (tl, tr, bl, br)
    }

    # Punch transparent holes into the foreground artwork wherever a slot's
    # BARE BLACK BACKGROUND shows (i.e. nothing was drawn over it), so the
    # image shows through there. Anything drawn on top of the placeholder in
    # the original design (dividers, borders, etc.) is left fully intact and
    # stays above the images.
    foreground = full_rgba.copy()
    slot_area = None
    for m in masks.values():
        area = m > 10
        slot_area = area if slot_area is None else (slot_area | area)
    rgb_sum = foreground[:, :, :3].astype("int32").sum(axis=2)
    near_black = rgb_sum < 30  # small tolerance for anti-aliased edges
    hole = slot_area & near_black
    foreground[hole, 3] = 0

    # --- Load, color-normalize, and cover-fit images ---
    print("Loading images...")
    scale_x = canvas_w / svg_w
    scale_y = canvas_h / svg_h

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    for slot, img_path in ((tl, tl_path), (tr, tr_path), (bl, bl_path), (br, br_path)):
        x0 = round(slot.x0 * scale_x)
        y0 = round(slot.y0 * scale_y)
        w = round(slot.width * scale_x)
        h = round(slot.height * scale_y)

        src_img = load_image_srgb(img_path)
        fitted = cover_fit_image(src_img.convert("RGB"), w, h).convert("RGBA")

        mask_crop = masks[slot.label][y0:y0 + h, x0:x0 + w]
        fitted.putalpha(Image.fromarray(mask_crop, mode="L"))

        canvas.alpha_composite(fitted, (x0, y0))

    # --- Composite foreground artwork (dividers/borders) on top ---
    overlay = Image.fromarray(foreground, mode="RGBA")
    canvas.alpha_composite(overlay, (0, 0))

    # --- Export ---
    out_path = (
        Path(args.out).expanduser().resolve()
        if args.out
        else script_dir / f"{svg_path.stem} - output.png"
    )
    print(f"\nExporting to {out_path} ...")
    final_rgb = canvas.convert("RGB")
    icc_bytes = ImageCms.ImageCmsProfile(_get_srgb_profile()).tobytes()
    final_rgb.save(str(out_path), format="PNG", icc_profile=icc_bytes)

    print(f"\nDone! Saved: {out_path}")


if __name__ == "__main__":
    main()
