# youtube_banner_parser.py

from PIL import Image
import pytesseract
import sys
import os
import re

def parse_banner(image_path):
    if not os.path.isfile(image_path):
        print(f"Error: File '{image_path}' not found.")
        return None
    
    try:
        image = Image.open(image_path)
    except Exception as e:
        print(f"Error opening image: {e}")
        return None

    try:
        text = pytesseract.image_to_string(image)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines
    except Exception as e:
        print(f"Error during OCR: {e}")
        return None

def extract_username_subscribers(line):
    match = re.search(r'(\d[\d,.]*[KM])', line, re.IGNORECASE)
    if match:
        subscribers = match.group(1)
        username = line[:match.start()].strip()
        return username, subscribers
    else:
        return line.strip(), ""

def format_banner(lines):
    if not lines or len(lines) < 2:
        return "Not enough text detected to parse banner."

    name = lines[0]
    username, subscribers = extract_username_subscribers(lines[1])
    description_lines = lines[2:4] if len(lines) > 2 else []
    description = " ".join(description_lines)

    formatted_text = (
        f"Name: {name}\n"
        f"Username: {username}\n"
        f"Subscribers: {subscribers}\n"
        f"Description: {description}"
    )
    return formatted_text

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python youtube_banner_parser.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]

    lines = parse_banner(image_path)
    
    if lines:
        formatted_text = format_banner(lines)
        print(formatted_text)
    else:
        print("No text extracted.")