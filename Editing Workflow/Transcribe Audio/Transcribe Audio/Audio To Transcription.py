# audio_to_transcript.py

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import sys
import os
import whisper
import math

WINDOW_SIZE = 10  # seconds

def format_time(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python audio_to_transcript.py <audio_file>")
        sys.exit(1)

    audio_path = sys.argv[1]
    if not os.path.exists(audio_path):
        print(f"File not found: {audio_path}")
        sys.exit(1)

    print("Loading model...")
    model = whisper.load_model("base")

    print("Transcribing with word timestamps...")
    result = model.transcribe(audio_path, word_timestamps=True)

    words = []
    for segment in result["segments"]:
        for word_info in segment.get("words", []):
            words.append(word_info)

    if not words:
        print("No words detected.")
        return

    total_duration = words[-1]["end"]
    total_windows = math.ceil(total_duration / WINDOW_SIZE)

    for i in range(total_windows):
        window_start = i * WINDOW_SIZE
        window_end = window_start + WINDOW_SIZE

        window_words = [
            w["word"].strip()
            for w in words
            if window_start <= w["start"] < window_end
        ]

        if window_words:
            print(f"[{format_time(window_start)} – {format_time(window_end)}]")
            print(" ".join(window_words))
            print()

if __name__ == "__main__":
    main()