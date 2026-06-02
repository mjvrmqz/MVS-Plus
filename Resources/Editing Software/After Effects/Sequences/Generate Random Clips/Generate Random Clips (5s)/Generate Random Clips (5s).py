import random
import subprocess
import yt_dlp
import os
import shutil

URL = "https://www.youtube.com/watch?v=VIDEO_ID"
CLIP_LENGTH = 5        # seconds per segment
REPEATS = 5            # number of random samples
TMP_DIR = "tmp_clips"
FINAL_OUTPUT = "random_compilation.mp4"

os.makedirs(TMP_DIR, exist_ok=True)

def get_duration(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info['duration']

def download_clip(url, start_time, duration, index):
    out = f"{TMP_DIR}/clip_{index}.mp4"

    cmd = [
        "yt-dlp", url,
        "-f", "mp4",
        "--external-downloader", "ffmpeg",
        "--external-downloader-args",
        f"ffmpeg_i:-ss {start_time} -t {duration}",
        "-o", out
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out

def concat_clips(file_list, output):
    list_file = "concat_list.txt"
    with open(list_file, "w") as f:
        for file in file_list:
            f.write(f"file '{file}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(list_file)

def main():
    duration = get_duration(URL)
    clips = []

    for i in range(REPEATS):
        max_start = max(0, duration - CLIP_LENGTH)
        start_time = round(random.uniform(0, max_start), 2)

        print(f"Sampling clip {i+1}: {start_time}s → {start_time + CLIP_LENGTH}s")
        clip_path = download_clip(URL, start_time, CLIP_LENGTH, i+1)
        clips.append(clip_path)

    concat_clips(clips, FINAL_OUTPUT)

    shutil.rmtree(TMP_DIR)
    print(f"Final video created: {FINAL_OUTPUT}")

if __name__ == "__main__":
    main()