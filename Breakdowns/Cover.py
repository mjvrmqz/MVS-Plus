#!/usr/bin/env python3
"""
notion_cover_collage.py

Reads the N most recent pages from a Notion database (FRAMES_DB_ID),
grabs the images found in each page's content blocks, composites them
into a moody, dark, tilted/blurred PNG collage, uploads the PNG directly
to Notion via the File Upload API, and sets it as that page's cover.

Env vars required:
  NOTION_KEY     - Notion integration token
  FRAMES_DB_ID   - Notion database ID to read pages from

Optional env vars:
  PAGE_LIMIT          - how many recent pages to process (default 20)
  COLLAGE_OUTPUT_DIR  - where to save generated collage images (default ./collages)

Usage:
  python notion_cover_collage.py
"""

import os
import io
import math
import random
import time
import requests
from PIL import Image, ImageFilter, ImageEnhance, ImageOps


def load_env_file():
    """
    Walk upward from this script's location looking for a .env file
    (e.g. at the top level of the MVS-Plus repo) and load any vars
    from it into os.environ if they aren't already set.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))

    while True:
        candidate = os.path.join(current_dir, ".env")
        if os.path.isfile(candidate):
            with open(candidate, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
            return candidate

        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            # reached filesystem root without finding a .env
            return None
        current_dir = parent_dir


load_env_file()

NOTION_KEY = os.environ.get("NOTION_KEY")
FRAMES_DB_ID = os.environ.get("FRAMES_DB_ID")
PAGE_LIMIT = int(os.environ.get("PAGE_LIMIT", "20"))
OUTPUT_DIR = os.environ.get("COLLAGE_OUTPUT_DIR", "./collages")

NOTION_VERSION = "2022-06-28"
NOTION_API_BASE = "https://api.notion.com/v1"

HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

# Final cover image dimensions (Notion covers display ~1500x600 cropped area)
CANVAS_W = 1500
CANVAS_H = 600


def query_recent_pages(db_id, limit=20):
    """Query the database, sorted by last_edited_time descending."""
    url = f"{NOTION_API_BASE}/databases/{db_id}/query"
    payload = {
        "page_size": min(limit, 100),
        "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])[:limit]


def get_block_children(block_id, start_cursor=None):
    url = f"{NOTION_API_BASE}/blocks/{block_id}/children"
    params = {"page_size": 100}
    if start_cursor:
        params["start_cursor"] = start_cursor
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()


def extract_image_urls_from_blocks(page_id):
    """Recursively walk a page's block children and collect image URLs."""
    image_urls = []

    def walk(block_id):
        cursor = None
        while True:
            data = get_block_children(block_id, cursor)
            for block in data.get("results", []):
                btype = block.get("type")
                if btype == "image":
                    img = block["image"]
                    if img["type"] == "external":
                        image_urls.append(img["external"]["url"])
                    elif img["type"] == "file":
                        image_urls.append(img["file"]["url"])
                # Recurse into children if block has them
                if block.get("has_children"):
                    walk(block["id"])
            if data.get("has_more"):
                cursor = data.get("next_cursor")
            else:
                break

    walk(page_id)
    return image_urls


DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def download_image(url, max_retries=4):
    backoff = 2
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=DOWNLOAD_HEADERS, timeout=20)
            if resp.status_code == 429:
                print(f"  [warn] 429 rate limited, retrying in {backoff}s "
                      f"(attempt {attempt}/{max_retries})...")
                time.sleep(backoff)
                backoff *= 2
                continue
            resp.raise_for_status()
            return Image.open(io.BytesIO(resp.content)).convert("RGBA")
        except Exception as e:
            if attempt == max_retries:
                print(f"  [warn] failed to download image after {max_retries} attempts: {e}")
                return None
            time.sleep(backoff)
            backoff *= 2
    return None


def make_tilted_layer(img, target_size, angle_range=(-25, 25)):
    """Scale an image to roughly fill target box, then rotate it for a tilted look."""
    target_w, target_h = target_size

    # Scale up a bit beyond target so rotation doesn't leave gaps
    scale_factor = 1.5
    img_ratio = img.width / img.height
    box_ratio = target_w / target_h

    if img_ratio > box_ratio:
        new_h = int(target_h * scale_factor)
        new_w = int(new_h * img_ratio)
    else:
        new_w = int(target_w * scale_factor)
        new_h = int(new_w / img_ratio)

    img = img.resize((new_w, new_h), Image.LANCZOS)

    angle = random.uniform(*angle_range)
    img = img.rotate(angle, expand=True, resample=Image.BICUBIC)

    return img


def darken_and_blur(img, blur_radius=6, darkness=0.45):
    """Apply moderate blur and darken the image."""
    blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Darken via brightness enhancement (darkness < 1 darkens)
    rgb = blurred.convert("RGB")
    enhancer = ImageEnhance.Brightness(rgb)
    darkened = enhancer.enhance(darkness)

    # Reduce saturation slightly for moodier feel
    color_enhancer = ImageEnhance.Color(darkened)
    darkened = color_enhancer.enhance(0.85)

    darkened = darkened.convert("RGBA")
    if blurred.mode == "RGBA":
        darkened.putalpha(blurred.split()[-1])

    return darkened


def build_collage(image_list, canvas_w=CANVAS_W, canvas_h=CANVAS_H):
    """
    Build a dark, tilted, blurred collage from a list of PIL Images.
    Images are scattered/overlapped across the canvas with slight rotation,
    then the whole composite gets a blur + dark overlay pass.
    """
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (8, 8, 10, 255))

    if not image_list:
        return canvas.convert("RGB")

    n = len(image_list)
    cols = max(1, math.ceil(math.sqrt(n * (canvas_w / canvas_h))))
    rows = max(1, math.ceil(n / cols))

    cell_w = canvas_w / cols
    cell_h = canvas_h / rows

    for idx, img in enumerate(image_list):
        col = idx % cols
        row = idx // cols

        cell_cx = int(col * cell_w + cell_w / 2)
        cell_cy = int(row * cell_h + cell_h / 2)

        # jitter the placement so it doesn't look like a strict grid
        jitter_x = random.randint(int(-cell_w * 0.2), int(cell_w * 0.2))
        jitter_y = random.randint(int(-cell_h * 0.2), int(cell_h * 0.2))

        tilted = make_tilted_layer(img, (int(cell_w * 1.3), int(cell_h * 1.3)))

        paste_x = cell_cx + jitter_x - tilted.width // 2
        paste_y = cell_cy + jitter_y - tilted.height // 2

        canvas.alpha_composite(tilted, dest=(paste_x, paste_y))

    # Global moderate blur + darken pass over the whole collage
    final = darken_and_blur(canvas, blur_radius=5, darkness=0.4)

    # Add a subtle dark vignette gradient overlay for extra mood
    vignette = Image.new("L", (canvas_w, canvas_h), 0)
    vignette_pixels = vignette.load()
    cx, cy = canvas_w / 2, canvas_h / 2
    max_dist = math.hypot(cx, cy)
    for x in range(0, canvas_w, 4):
        for y in range(0, canvas_h, 4):
            dist = math.hypot(x - cx, y - cy) / max_dist
            val = int(min(255, dist * 160))
            for dx in range(4):
                for dy in range(4):
                    if x + dx < canvas_w and y + dy < canvas_h:
                        vignette_pixels[x + dx, y + dy] = val

    black_layer = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
    final_rgb = final.convert("RGB")
    final_rgb = Image.composite(black_layer, final_rgb, vignette)

    return final_rgb


def upload_to_notion(image_path):
    """
    Upload a local image file directly to Notion using Notion's File Upload API,
    and return a file_upload id that can be used as a page cover.

    Flow:
      1. POST /v1/file_uploads to create an upload object
      2. POST /v1/file_uploads/{id}/send with the file bytes (multipart)
      3. Use the returned file_upload id when setting the page cover
    """
    filename = os.path.basename(image_path)

    create_url = f"{NOTION_API_BASE}/file_uploads"
    create_resp = requests.post(
        create_url,
        headers={
            "Authorization": f"Bearer {NOTION_KEY}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
        json={"filename": filename},
    )
    create_resp.raise_for_status()
    upload_obj = create_resp.json()
    file_upload_id = upload_obj["id"]
    send_url = upload_obj["upload_url"]

    with open(image_path, "rb") as f:
        files = {"file": (filename, f, "image/png")}
        send_resp = requests.post(
            send_url,
            headers={
                "Authorization": f"Bearer {NOTION_KEY}",
                "Notion-Version": NOTION_VERSION,
            },
            files=files,
        )
    send_resp.raise_for_status()

    return file_upload_id


def set_page_cover_from_upload(page_id, file_upload_id):
    url = f"{NOTION_API_BASE}/pages/{page_id}"
    payload = {
        "cover": {
            "type": "file_upload",
            "file_upload": {"id": file_upload_id},
        }
    }
    resp = requests.patch(url, headers=HEADERS, json=payload)
    resp.raise_for_status()
    return resp.json()


def get_page_title(page):
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            if title_parts:
                return "".join([t.get("plain_text", "") for t in title_parts])
    return page.get("id", "untitled")


def main():
    if not NOTION_KEY or not FRAMES_DB_ID:
        raise RuntimeError("NOTION_KEY and FRAMES_DB_ID env vars must be set.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Querying {PAGE_LIMIT} most recent pages from database {FRAMES_DB_ID}...")
    pages = query_recent_pages(FRAMES_DB_ID, PAGE_LIMIT)
    print(f"Found {len(pages)} pages.")

    for page in pages:
        page_id = page["id"]
        title = get_page_title(page)
        print(f"\nProcessing page: {title} ({page_id})")

        image_urls = extract_image_urls_from_blocks(page_id)
        print(f"  Found {len(image_urls)} image(s) in page content.")

        if not image_urls:
            print("  No images found, skipping.")
            continue

        images = []
        for url in image_urls:
            img = download_image(url)
            if img is not None:
                images.append(img)

        if not images:
            print("  No images successfully downloaded, skipping.")
            continue

        collage = build_collage(images)

        safe_name = "".join(c if c.isalnum() else "_" for c in title)[:50]
        out_path = os.path.join(OUTPUT_DIR, f"{safe_name}_{page_id}.png")
        collage.save(out_path, "PNG")
        print(f"  Saved collage to {out_path}")

        try:
            file_upload_id = upload_to_notion(out_path)
            print(f"  Uploaded to Notion (file_upload id: {file_upload_id})")
            set_page_cover_from_upload(page_id, file_upload_id)
            print("  Page cover updated.")
        except Exception as e:
            print(f"  [warn] failed to upload/set cover: {e}")

        time.sleep(1)


if __name__ == "__main__":
    main()