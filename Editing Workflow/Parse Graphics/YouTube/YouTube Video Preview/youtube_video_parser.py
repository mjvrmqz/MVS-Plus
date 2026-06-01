from PIL import Image, ImageOps
import pytesseract
import sys
import os
import re

# Words to ignore completely
IGNORE_KEYWORDS = ["subscribe", "share", "ask", "join", "save"]

def preprocess_image(image):
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)
    w, h = gray.size
    gray = gray.resize((w * 2, h * 2), Image.BICUBIC)
    return gray

def line_is_noise(line):
    line_lower = line.lower()
    return any(word in line_lower for word in IGNORE_KEYWORDS)

def clean_channel_name(line):
    # Remove all UI words
    for word in IGNORE_KEYWORDS:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        line = pattern.sub("", line)

    # Keep only letters, spaces, and @ symbol
    line = re.sub(r"[^a-zA-Z@ ]", "", line)

    # Remove extra spaces
    line = " ".join(line.split())

    return line

def parse_video(lines):
    # Clean OCR lines: remove empty + UI noise
    cleaned_lines = [line.strip() for line in lines if line.strip() and not line_is_noise(line)]

    if len(cleaned_lines) < 2:
        return "Not enough text extracted."

    # Title = longest line
    sorted_lines = sorted(cleaned_lines, key=lambda x: len(x), reverse=True)
    title = sorted_lines[0]

    # Channel Name = second-longest line, cleaned
    remaining_lines = [line for line in cleaned_lines if line != title]
    channel_name = clean_channel_name(remaining_lines[0]) if remaining_lines else ""

    return (
        f"Title: {title}\n"
        f"Channel Name: {channel_name}"
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python youtube_video_parser.py <image_file>")
        sys.exit(1)

    image_path = sys.argv[1]

    if not os.path.isfile(image_path):
        print(f"Error: File '{image_path}' not found.")
        sys.exit(1)

    try:
        image = Image.open(image_path)
        image = preprocess_image(image)

        text = pytesseract.image_to_string(image, config="--psm 6")
        lines = text.splitlines()

    except Exception as e:
        print(f"OCR error: {e}")
        sys.exit(1)

    result = parse_video(lines)
    print(result)