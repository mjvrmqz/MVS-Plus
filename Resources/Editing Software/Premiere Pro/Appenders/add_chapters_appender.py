#!/usr/bin/env python3

import sys
import re
from pathlib import Path

# ---- CONFIG ----
JSX_PATH = Path("/Users/mjvrmqz/Personal/Scripts/Editing Software/Premiere Pro/Add Chapters.jsx")
MAX_CHAPTERS = 10
MARKER_BLOCK_START = "// CHAPTER MARKERS START"
MARKER_BLOCK_END = "// CHAPTER MARKERS END"
DEFAULT_FPS = 30
# ----------------

def timecode_to_seconds(tc, fps=DEFAULT_FPS):
    parts = list(map(int, tc.split(":")))
    if len(parts) == 4:  # HH:MM:SS:FF
        h, m, s, f = parts
        return h*3600 + m*60 + s + f/fps
    elif len(parts) == 3:  # HH:MM:SS
        h, m, s = parts
        return h*3600 + m*60 + s
    elif len(parts) == 2:  # MM:SS
        m, s = parts
        return m*60 + s
    else:
        raise ValueError(f"Invalid timecode: {tc}")

def escape_js_string(s):
    # Escape quotes and remove newlines
    s = s.replace('"', "'")
    s = s.replace("\n", " ").replace("\r", "")
    return s.strip()

def parse_input(text):
    text = text.replace("–", "-").replace("—", "-")
    chapters = []

    raw_chapters = re.split(r"\n\n+", text.strip())
    for raw in raw_chapters:
        lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
        if len(lines) < 2:
            continue

        # Chapter number & title
        header_match = re.match(r"Chapter\s+(\d+):\s*(.+)", lines[0])
        if not header_match:
            continue
        number = int(header_match.group(1))
        title = escape_js_string(header_match.group(2))

        # Timecode
        tc_match = re.match(r"Timecode:\s*([\d:]+)\s*-\s*([\d:]+)", lines[1])
        if not tc_match:
            continue
        start = timecode_to_seconds(tc_match.group(1))
        end = timecode_to_seconds(tc_match.group(2))

        chapters.append({
            "number": number,
            "title": title,
            "start": start,
            "end": end
        })

    if len(chapters) > MAX_CHAPTERS:
        raise ValueError(f"Too many chapters ({len(chapters)}). Max allowed is {MAX_CHAPTERS}.")
    return chapters

def generate_marker_lines(chapters):
    lines = []
    for ch in chapters:
        lines.append(f"    var m{ch['number']} = markers.createMarker({ch['start']});")
        lines.append(f"    m{ch['number']}.end = {ch['end']};")
        lines.append(f"    m{ch['number']}.name = \"Chapter {ch['number']}: {ch['title']}\";")
        lines.append("")  # blank line
    return "\n".join(lines)

def main():
    input_text = sys.stdin.read().strip()
    if not input_text:
        print("No input provided.")
        sys.exit(1)

    chapters = parse_input(input_text)
    new_marker_block = generate_marker_lines(chapters)

    try:
        jsx_text = JSX_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"JSX file not found: {JSX_PATH}")
        sys.exit(1)

    pattern = re.compile(
        r"\s*" + re.escape(MARKER_BLOCK_START) + r".*?" + re.escape(MARKER_BLOCK_END) + r"\s*",
        re.DOTALL
    )
    replacement = f"{MARKER_BLOCK_START}\n{new_marker_block}{MARKER_BLOCK_END}"

    if not pattern.search(jsx_text):
        print("Marker block placeholder not found in JSX. Ensure it has start/end comments.")
        sys.exit(1)

    updated_jsx = pattern.sub(replacement, jsx_text)
    JSX_PATH.write_text(updated_jsx, encoding="utf-8")
    print(f"Updated {len(chapters)} chapters in {JSX_PATH}")

if __name__ == "__main__":
    main()