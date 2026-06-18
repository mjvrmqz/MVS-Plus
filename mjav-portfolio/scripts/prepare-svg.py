#!/usr/bin/env python3
"""
prepare-svg.py

Copies the source mjavfx.svg into the Astro public/ folder so it gets
served as /site-bg.svg at runtime. Run from mjav-portfolio/ directory.

Usage:
  python3 scripts/prepare-svg.py <source-svg> <dest-svg>
"""
import shutil
import sys
import os

if len(sys.argv) < 3:
    print("usage: prepare-svg.py <source> <dest>")
    sys.exit(1)

src  = sys.argv[1]
dest = sys.argv[2]

if not os.path.isfile(src):
    print(f"error: source SVG not found at {src}")
    print("pass the path explicitly: python3 scripts/prepare-svg.py <path-to-mjavfx.svg> <dest>")
    sys.exit(1)

os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
shutil.copy2(src, dest)
print(f"copied {src} -> {dest}  ({os.path.getsize(dest)} bytes)")
