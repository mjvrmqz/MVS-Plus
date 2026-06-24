# MVS Studios · Hub

Local web app for uploading Frames, Clips, and Lessons to Notion.

## Setup

**Requirements:** Python 3.9+, `ffmpeg` installed and on your PATH.

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create your `.env` file

Copy `.env.example` → `.env` and fill in your values:

```
NOTION_KEY=secret_...
INSPIRATION_DB_ID=...
CLIPS_DB_ID=...
LESSONS_DB_ID=...
```

DB IDs are the 32-character strings in your Notion database URLs.

### 3. Run

```bash
python Hub.py
```

The app opens automatically at **http://localhost:5000**.

---

## ffmpeg install

**Mac:** `brew install ffmpeg`  
**Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH, or use `winget install ffmpeg`.
