import re
import sys

# Path to your JSX file
jsx_path = "/Users/mjvrmqz/Personal/Scripts/Editing Software/Premiere Pro/Add Builder Movements.jsx"

# Read the movements string from command line argument
if len(sys.argv) < 2:
    print("Usage: python appender.py '<movements_string>'")
    sys.exit(1)

gpt_string = sys.argv[1]

def parse_movements(gpt_string):
    lines = [line.strip() for line in gpt_string.splitlines() if line.strip()]
    calls = []
    for i in range(0, len(lines), 2):
        name = lines[i]
        times = lines[i + 1] if i + 1 < len(lines) else None
        if not times:
            continue
        match = re.match(r"(\d+):(\d+):(\d+)–(\d+):(\d+):(\d+)", times)
        if match:
            h1, m1, s1, h2, m2, s2 = map(int, match.groups())
            start_sec = h1 * 3600 + m1 * 60 + s1
            end_sec = h2 * 3600 + m2 * 60 + s2
            calls.append(f'    addMovement("{name}", {start_sec}, {end_sec});')
    return "\n".join(calls)

# Read JSX file
with open(jsx_path, "r") as f:
    jsx_content = f.read()

# Replace the hardcoded section
new_section = f"// ==============================\n{parse_movements(gpt_string)}\n// =============================="
jsx_content = re.sub(r"// ==============================\n[\s\S]*?// ==============================", new_section, jsx_content)

# Write JSX back
with open(jsx_path, "w") as f:
    f.write(jsx_content)

print("Add Builder Movements.jsx updated.")