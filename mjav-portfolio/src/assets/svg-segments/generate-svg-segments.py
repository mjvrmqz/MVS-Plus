#!/usr/bin/env python3
"""
generate-svg-segments.py

Splits the original mjavfx.svg (863x2351, raw Figma export) into five
section files using viewBox windowing. Each output file is a FULL COPY
of the original's body + defs, just with a different viewBox y-offset.
This guarantees nothing breaks (every filter, gradient, mask, and the
embedded avatar PNG resolves correctly in every output file) at the
cost of file size (~250KB each, since the ~58KB defs block and ~190KB
body are duplicated five times). See SVG_SEGMENTS.md for the rationale,
the exact y-coordinate boundaries, and a path-index reference for anyone
who wants to trim the duplicated defs down per-segment later.

Usage:
    python3 generate-svg-segments.py /path/to/mjavfx.svg ./src/assets/svg-segments

If no arguments given, defaults to looking for mjavfx.svg in the repo
root and writing to src/assets/svg-segments/ relative to this script's
location (i.e. run it from anywhere, paths are resolved relative to
this file, not relative to your shell's cwd).
"""

import os
import re
import sys

# Section boundaries in the original 2351px-tall canvas. See
# SVG_SEGMENTS.md for how these were determined (pixel-row inspection
# of rendered crops, cross-checked against path anchor y-coordinates).
SECTIONS = {
    "nav":            (0, 55),
    "home":           (55, 614),
    "avatars":        (614, 747),
    "work-showcase":  (747, 1760),
    "contact":        (1760, 2351),
}

CANVAS_WIDTH = 863


def split_svg(source_path: str, output_dir: str) -> None:
    with open(source_path, "r", encoding="utf-8") as f:
        content = f.read()

    defs_match = re.search(r"<defs>.*?</defs>", content, re.DOTALL)
    if not defs_match:
        raise ValueError("Could not find <defs>...</defs> block in source SVG")
    defs_content = defs_match.group(0)

    svg_open_match = re.search(r"<svg[^>]*>", content)
    if not svg_open_match:
        raise ValueError("Could not find opening <svg> tag in source SVG")

    body_start = content.index(svg_open_match.group(0)) + len(svg_open_match.group(0))
    body_end = content.index("<defs>")
    body = content[body_start:body_end]

    os.makedirs(output_dir, exist_ok=True)

    for name, (y0, y1) in SECTIONS.items():
        height = y1 - y0
        svg = (
            f'<svg width="{CANVAS_WIDTH}" height="{height}" '
            f'viewBox="0 {y0} {CANVAS_WIDTH} {height}" fill="none" '
            f'xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink">\n'
            f"{body}{defs_content}\n</svg>"
        )
        out_path = os.path.join(output_dir, f"{name}.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"wrote {out_path}  (y={y0}-{y1}, height={height}, {len(svg)} bytes)")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))

    default_source = os.path.join(repo_root, "mjavfx.svg")
    default_output = os.path.join(script_dir)

    source = sys.argv[1] if len(sys.argv) > 1 else default_source
    output = sys.argv[2] if len(sys.argv) > 2 else default_output

    if not os.path.isfile(source):
        print(f"error: source SVG not found at {source}")
        print("pass the path explicitly: python3 generate-svg-segments.py <path-to-mjavfx.svg> <output-dir>")
        sys.exit(1)

    split_svg(source, output)
