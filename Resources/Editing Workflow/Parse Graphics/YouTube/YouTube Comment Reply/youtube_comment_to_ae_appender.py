# youtube_comment_to_ae_editor.py
import sys
import os

# ============================
# Configuration
# ============================

# Path to your JSX file
JSX_PATH = "/Users/mjvrmqz/Downloads/Scripts/Apple Shortcuts/ProjectPhases/youtube_comment_to_ae.jsx"

# ============================
# Main Logic
# ============================

# Read comment text from stdin (Shortcuts input)
comment_blob = sys.stdin.read().strip()

# Convert multi-line comment into single line with ' | ' separators
lines = [line.strip() for line in comment_blob.splitlines() if line.strip()]
comment_line = " | ".join(lines)

# Prepare the replacement line for JSX
replacement = f'var commentText = "{comment_line}";'

# Read the existing JSX file
if not os.path.exists(JSX_PATH):
    print(f"Error: JSX file not found at {JSX_PATH}")
    sys.exit(1)

with open(JSX_PATH, "r", encoding="utf-8") as f:
    jsx_lines = f.readlines()

# Replace the line containing 'var commentText ='
for i, line in enumerate(jsx_lines):
    if "var commentText" in line:
        jsx_lines[i] = replacement + "\n"
        break
else:
    print("Error: 'var commentText' line not found in JSX file.")
    sys.exit(1)

# Write the updated JSX back
with open(JSX_PATH, "w", encoding="utf-8") as f:
    f.writelines(jsx_lines)

print(f"Updated JSX comment to:\n{replacement}")