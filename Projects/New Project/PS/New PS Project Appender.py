import sys
import re

input_text = sys.stdin.read().strip()

if not input_text and len(sys.argv) > 1:
    input_text = "\n".join(sys.argv[1:])

if not input_text:
    raise ValueError("No input received from Shortcuts")

name_match = re.search(r"Name:\s*(.*)", input_text)
path_match = re.search(r"File Path:\s*(.*)", input_text)

if not name_match or not path_match:
    raise ValueError("Input format invalid. Expected 'Name:' and 'File Path:' lines")

project_filename = name_match.group(1).strip() + ".psd"
folder_path = path_match.group(1).strip()

JSX_PATH = "/Users/mjvrmqz/Personal/Scripts/Editing Software/Photoshop/Automation/Create New Project/Create New Project.jsx"

with open(JSX_PATH, "r") as f:
    jsx_content = f.read()

jsx_content = re.sub(r'var folderPath = ".*?";', f'var folderPath = "{folder_path}";', jsx_content)
jsx_content = re.sub(r'var projectName = ".*?";', f'var projectName = "{project_filename}";', jsx_content)

with open(JSX_PATH, "w") as f:
    f.write(jsx_content)

print("SUCCESS: Photoshop JSX was updated")
print(f"Project Name: {project_filename}")
print(f"Folder Path : {folder_path}")
print(f"JSX File    : {JSX_PATH}")
