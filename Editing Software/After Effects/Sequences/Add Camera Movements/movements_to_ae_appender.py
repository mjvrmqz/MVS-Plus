import re
import sys

input_text = sys.argv[1]
jsx_file = "movements_to_ae.jsx"

movements = []
chapters = {}
section = None
for line in input_text.splitlines():
    line = line.strip()
    if not line: continue
    if line.startswith("==="):
        if "MOVEMENTS" in line: section = "movements"
        elif "CHAPTERS" in line: section = "chapters"
        continue
    if section == "movements":
        parts = line.split(":")
        if len(parts) == 2: movements.append(parts[1].strip())
    elif section == "chapters":
        parts = line.split(":")
        if len(parts) == 2: chapters[parts[0].strip()] = int(parts[1].strip())

with open(jsx_file, "r") as f:
    jsx_content = f.read()

movement_js_array = ','.join(f'"{m}"' for m in movements)
movement_js_code = f"var movementSequence = [\n    {movement_js_array}\n];"
jsx_content = re.sub(r"var movementSequence = \[.*?\];", movement_js_code, jsx_content, flags=re.DOTALL)

chapter_js_entries = ',\n    '.join(f'"{k}": {v}' for k,v in chapters.items())
chapter_js_code = f"var chapterData = {{\n    {chapter_js_entries}\n}};"
jsx_content = re.sub(r"var chapterData = \{.*?\};", chapter_js_code, jsx_content, flags=re.DOTALL)

with open(jsx_file, "w") as f:
    f.write(jsx_content)

print("movements_to_ae.jsx updated successfully.")
