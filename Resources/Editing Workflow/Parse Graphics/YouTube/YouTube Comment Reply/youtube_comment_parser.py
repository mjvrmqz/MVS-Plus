from PIL import Image
import pytesseract
import sys
import re

# Get file path from argument
if len(sys.argv) < 2:
    print("Usage: python3 screenshot_reader.py /path/to/screenshot.png")
    sys.exit(1)

screenshot_path = sys.argv[1]

# Load image
img = Image.open(screenshot_path)

# OCR
lines = [line.strip() for line in pytesseract.image_to_string(img).split('\n') if line.strip()]

if len(lines) < 2:
    print("Could not detect comment properly.")
    sys.exit(1)

# ---------------------------
# Username and Date Parsing
# ---------------------------
first_line = lines[0]

# Find first @ and capture contiguous username
username_match = re.search(r'@[\S]+', first_line)
if username_match:
    username = username_match.group(0)
    # Everything after the username is considered date
    date = first_line[username_match.end():].strip()
    # Remove leading tilde and optional "(edited)" if present
    date = date.lstrip('~ ').replace('(edited)', '').strip() or "N/A"
else:
    username = first_line
    date = "N/A"

# ---------------------------
# Likes Parsing
# ---------------------------
likes_line = lines[-1]
likes_match = re.search(r'([\d,.]+)([kK]?)', likes_line)
if likes_match:
    number = likes_match.group(1).replace(',', '')
    k_modifier = likes_match.group(2).lower()
    if k_modifier == 'k':
        likes = str(int(float(number) * 1000))
    else:
        likes = str(int(float(number)))
else:
    likes = "N/A"

# ---------------------------
# Comment Parsing
# ---------------------------
comment_lines = lines[1:-1]  # everything between first and last line
comment_text = " ".join(comment_lines)

# Clean spacing and fix OCR artifacts
comment_text = re.sub(r'\s+', ' ', comment_text).strip()
comment_text = re.sub(r'\s?\|\s?', " I ", comment_text)

# ---------------------------
# Final Output
# ---------------------------
print(f"Username: {username}")
print(f"Date: {date}")
print(f"Comment: {comment_text}")
print(f"Likes: {likes}")