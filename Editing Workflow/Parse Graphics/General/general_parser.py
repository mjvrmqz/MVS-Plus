from PIL import Image, ImageOps
import pytesseract
import sys
import os

def preprocess_image(image):
    # Convert to grayscale and enhance contrast
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)

    # Optional: upscale to improve OCR on small text
    w, h = gray.size
    gray = gray.resize((w * 2, h * 2), Image.BICUBIC)

    return gray

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python general_parser.py <image_file>")
        sys.exit(1)

    image_path = sys.argv[1]

    if not os.path.isfile(image_path):
        print(f"Error: File '{image_path}' not found.")
        sys.exit(1)

    try:
        image = Image.open(image_path)
        image = preprocess_image(image)

        # Run OCR
        text = pytesseract.image_to_string(image, config="--psm 6")

        print(text)

    except Exception as e:
        print(f"OCR error: {e}")
        sys.exit(1)