import sys
import re
from pathlib import Path

jsx_path = Path("/Users/mjvrmqz/Personal/Scripts/Editing Software/Premiere Pro/Add Builder Assets.jsx")
gpt_string = sys.argv[1]

def timecode_to_seconds(tc):
    h, m, s = tc.split(":")
    return int(h)*3600 + int(m)*60 + float(s)

# Split by segments
segment_pattern = r"Timestamp:\s*(\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2})\n\nTranscript:(.*?)\n\nBackground:.*?\n\nPuppet:(.*?)\n\nIcon:(.*?)\n\n"
segments = re.findall(segment_pattern, gpt_string, re.DOTALL)

if not segments:
    print("No valid segments found.")
    exit()

js_array_entries = []
for start_tc, end_tc, transcript, puppet_block, icon_block in segments:
    start_sec = int(timecode_to_seconds(start_tc))
    end_sec = int(timecode_to_seconds(end_tc))
    puppets = [p.strip() for p in puppet_block.strip().split("\n") if p.strip()]
    icons = [i.strip() for i in icon_block.strip().split("\n") if i.strip()]
    puppet_count = len(puppets)
    icon_count = len(icons)
    max_puppet_layer = puppet_count if puppet_count > 0 else 1
    max_icon_layer = icon_count if icon_count > 0 else 1
    js_array_entries.append(f"[{start_sec},{end_sec},{puppet_count},{max_puppet_layer},{icon_count},{max_icon_layer}]")

js_array_string = "var storyboardTimestamps = [\n    " + ",\n    ".join(js_array_entries) + "\n];"

# Read existing JSX
with open(jsx_path, "r") as f:
    jsx_content = f.read()

# Replace the variable
new_content = re.sub(
    r"var storyboardTimestamps\s*=\s*\[.*?\];",
    js_array_string,
    jsx_content,
    flags=re.DOTALL
)

with open(jsx_path, "w") as f:
    f.write(new_content)

print(f"Updated JSX with {len(js_array_entries)} storyboard timestamps.")