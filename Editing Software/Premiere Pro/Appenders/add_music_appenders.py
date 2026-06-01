#!/usr/bin/env python3
import sys
import os
import re

JSX_FILE = "/Users/mjvrmqz/Personal/Scripts/Editing Software/Premiere Pro/Add Music.jsx"

def extract_paths_with_ids(text):
    """
    Extract paths and generate chapter IDs (C#MC##) per order in chapter.
    """
    paths_with_ids = []
    current_chapter = None
    order_counter = 1

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        chapter_match = re.match(r'Chapter\s+(\d+)', line)
        if chapter_match:
            current_chapter = int(chapter_match.group(1))
            order_counter = 1
            continue

        if line.startswith("/Users/") and current_chapter is not None:
            id_str = f"C{current_chapter}MC{order_counter:02}"
            paths_with_ids.append({"id": id_str, "path": line})
            order_counter += 1

    return paths_with_ids

def build_js_arrays(paths_with_ids):
    """
    Build two JS arrays: paths and IDs
    """
    paths_array = []
    ids_array = []

    for p in paths_with_ids:
        path_escaped = p["path"].replace("\\", "\\\\").replace('"', '\\"')
        paths_array.append(f'"{path_escaped}"')
        ids_array.append(f'"{p["id"]}"')

    replacement_paths = f"var inputPaths = [{','.join(paths_array)}];"
    replacement_ids = f"var inputIDs = [{','.join(ids_array)}];"

    return replacement_paths, replacement_ids

def update_jsx(paths_with_ids):
    if not os.path.exists(JSX_FILE):
        print(f"JSX file not found: {JSX_FILE}")
        return False

    with open(JSX_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    replacement_paths, replacement_ids = build_js_arrays(paths_with_ids)

    # Replace inputPaths and inputIDs
    content = re.sub(r'var\s+inputPaths\s*=\s*\[.*?\];', replacement_paths, content, flags=re.DOTALL)
    content = re.sub(r'var\s+inputIDs\s*=\s*\[.*?\];', replacement_ids, content, flags=re.DOTALL)

    with open(JSX_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Updated JSX with {len(paths_with_ids)} paths.")
    return True

def main():
    input_text = sys.stdin.read()

    if not input_text.strip():
        print("No input received.")
        return

    paths_with_ids = extract_paths_with_ids(input_text)

    if not paths_with_ids:
        print("No valid /Users/ paths found.")
        return

    update_jsx(paths_with_ids)

if __name__ == "__main__":
    main()