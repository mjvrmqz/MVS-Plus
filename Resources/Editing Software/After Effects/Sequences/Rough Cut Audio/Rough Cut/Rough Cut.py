import librosa
import numpy as np
import csv
import os

# ===== CONFIG =====
AUDIO_FILE = "/Users/mjvrmqz/Personal/MVS Studios Assets/Niches/YouTube Documentary/Projects/Project 34856/Sound/SAUD_RW01.mp3"
FRAME_RATE = 29.97
WINDOW_MS = 40               # RMS window size (larger → smoother)
MIN_SILENCE_LEN = 0.14       # minimum silence to mark (seconds)
ADAPTIVE_THRESH_FACTOR = 0.2  # silence is below X% of local median RMS
LOCAL_MEDIAN_WINDOW = 2.0    # seconds, rolling window for median
MERGE_CLOSE_SILENCES = 0.2   # seconds, merge silences closer than this

OUTPUT_CSV = os.path.join(os.path.dirname(AUDIO_FILE), "rough_cut_markers.csv")

# ===== LOAD AUDIO =====
print("Loading audio...")
y, sr = librosa.load(AUDIO_FILE, sr=None, mono=True)

# ===== RMS WINDOWING =====
hop_length = int(sr * (WINDOW_MS / 1000))
frame_length = hop_length

rms = librosa.feature.rms(
    y=y,
    frame_length=frame_length,
    hop_length=hop_length
)[0]

# Rolling median for adaptive threshold
median_window_frames = max(1, int(LOCAL_MEDIAN_WINDOW * sr / hop_length))
rms_padded = np.pad(rms, (median_window_frames//2,), mode='edge')
local_medians = np.convolve(rms_padded, np.ones(median_window_frames)/median_window_frames, mode='valid')

# Threshold in amplitude
thresholds = local_medians * ADAPTIVE_THRESH_FACTOR

# ===== DETECT SILENCE =====
silent_sections = []
in_silence = False
start_time = 0

for i, (amp, thresh) in enumerate(zip(rms, thresholds)):
    time_sec = i * (hop_length / sr)

    if amp < thresh:
        if not in_silence:
            in_silence = True
            start_time = time_sec
    else:
        if in_silence:
            end_time = time_sec
            if end_time - start_time >= MIN_SILENCE_LEN:
                silent_sections.append((start_time, end_time))
            in_silence = False

# Handle trailing silence
if in_silence:
    end_time = len(y) / sr
    if end_time - start_time >= MIN_SILENCE_LEN:
        silent_sections.append((start_time, end_time))

# ===== MERGE CLOSE SILENCES =====
merged = []
for s, e in silent_sections:
    if merged and s - merged[-1][1] <= MERGE_CLOSE_SILENCES:
        merged[-1] = (merged[-1][0], e)
    else:
        merged.append((s, e))

silent_sections = merged

# ===== FRAME SNAP =====
def snap_to_frame(time_sec, fps):
    return round(time_sec * fps) / fps

silent_sections = [(snap_to_frame(s, FRAME_RATE), snap_to_frame(e, FRAME_RATE)) for s, e in silent_sections]

# ===== SMPTE CONVERSION =====
def seconds_to_smpte(sec, fps):
    total_frames = round(sec * fps)
    hours = int(total_frames // (fps * 3600))
    total_frames %= int(fps * 3600)
    minutes = int(total_frames // (fps * 60))
    total_frames %= int(fps * 60)
    seconds = int(total_frames // fps)
    frames = int(total_frames % fps)
    return f"{hours:02d};{minutes:02d};{seconds:02d};{frames:02d}"

silent_smpte = [(seconds_to_smpte(s, FRAME_RATE), seconds_to_smpte(e, FRAME_RATE)) for s, e in silent_sections]

# ===== SAVE CSV =====
with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Start (SMPTE)", "End (SMPTE)"])
    writer.writerows(silent_smpte)

print(f"Detected {len(silent_smpte)} silent sections.")
print(f"Saved to: {OUTPUT_CSV}")