# youtube_preview_parser.py (clean Date output)

from PIL import Image
import pytesseract
import sys
import os
import re

def parse_preview(lines):
    meaningful_lines = [line.strip() for line in lines if line.strip()]
    if not meaningful_lines:
        return "No text extracted."

    # Title: combine first two lines
    title_lines = meaningful_lines[:2] if len(meaningful_lines) >= 2 else meaningful_lines[:1]
    title = " ".join(title_lines).strip()

    # Channel Name: third line
    channel_name = meaningful_lines[2] if len(meaningful_lines) >= 3 else ""

    # Views and Date: fourth line
    views = ""
    date = ""
    if len(meaningful_lines) >= 4:
        last_line = meaningful_lines[3]
        # Try splitting by bullet first
        if '·' in last_line:
            parts = last_line.split("·")
            left, right = parts[0].strip(), parts[1].strip()
            if re.search(r'\d[\d,.]*[KM]', left, re.IGNORECASE):
                views = left
                date = right
            else:
                views = right
                date = left
        else:
            # Fallback: find Views by K/M
            match = re.search(r'(\d[\d,.]*[KM])', last_line, re.IGNORECASE)
            if match:
                views = match.group(1)
                # Everything after Views is Date
                date_idx = last_line.find(views) + len(views)
                date = last_line[date_idx:].strip()
                # Remove extra words like "views" or "-" at the start
                date = re.sub(r'^(views\s*-?\s*)', '', date, flags=re.IGNORECASE)
            else:
                views = last_line
                date = ""

    formatted_text = (
        f"Title: {title}\n"
        f"Channel Name: {channel_name}\n"
        f"Views: {views}\n"
        f"Date: {date}"
    )

    return formatted_text

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python youtube_preview_parser.py <image_file>")
        sys.exit(1)

    image_path = sys.argv[1]
    if not os.path.isfile(image_path):
        print(f"Error: File '{image_path}' not found.")
        sys.exit(1)

    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        lines = text.splitlines()
    except Exception as e:
        print(f"OCR error: {e}")
        sys.exit(1)

    parsed_text = parse_preview(lines)
    print(parsed_text)