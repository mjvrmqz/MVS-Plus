import os
from pathlib import Path

# Folder to search
folder_path = "/Users/mjvrmqz/Downloads/Video Editing Assets/Niches/YouTube Documentary/Projects/Project 59673"

# Allowed file extensions for assets
ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".psd", ".tif", ".tiff", ".webp", ".avif"
}

latest_file = None
latest_mtime = 0

for root, dirs, files in os.walk(folder_path):
    for f in files:
        # Skip hidden/system files
        if f.startswith("."):
            continue

        file_path = Path(root) / f
        # Skip files without allowed extension
        if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue

        # Check last modified time
        mtime = file_path.stat().st_mtime
        if mtime > latest_mtime:
            latest_mtime = mtime
            latest_file = file_path

if latest_file:
    print(str(latest_file))
else:
    print("")  # nothing found
