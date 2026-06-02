import sys
import os

if len(sys.argv) < 2:
    print("No file path provided")
    sys.exit(1)

file_path = sys.argv[1].strip()  # remove accidental line breaks
if not os.path.exists(file_path):
    print(f"File does not exist: {file_path}")
    sys.exit(1)

jsx_path = "/Users/mjvrmqz/Downloads/Scripts/Photoshop/Import Latest Asset.jsx"
if not os.path.exists(jsx_path):
    print(f"JSX file does not exist: {jsx_path}")
    sys.exit(1)

# Escape double quotes in the path
safe_path = file_path.replace('"', '\\"')

with open(jsx_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
found = False
for line in lines:
    if "var shortcutFilePath =" in line:
        # Replace entire line with clean, single-line JS
        new_lines.append(f'    var shortcutFilePath = "{safe_path}";\n')
        found = True
    else:
        new_lines.append(line)

if not found:
    print("No shortcutFilePath line found in JSX")
    sys.exit(1)

with open(jsx_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"JSX updated with: {file_path}")
sys.exit(0)