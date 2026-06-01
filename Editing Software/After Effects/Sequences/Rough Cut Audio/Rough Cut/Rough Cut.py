import librosa
import numpy as np
import csv
import os

AUDIO_FILE = "/Users/mjvrmqz/Personal/MVS Studios Assets/Niches/YouTube Documentary/Projects/Project 34856/Sound/SAUD_RW01.mp3"
FRAME_RATE = 29.97
WINDOW_MS = 40
MIN_SILENCE_LEN = 0.14
ADAPTIVE_THRESH_FACTOR = 0.2
LOCAL_MEDIAN_WINDOW = 2.0
MERGE_CLOSE_SILENCES = 0.2
OUTPUT_CSV = os.path.join(os.path.dirname(AUDIO_FILE), "rough_cut_markers.csv")

print("Loading audio...")
y, sr = librosa.load(AUDIO_FILE, sr=None, mono=True)
hop_length = int(sr * (WINDOW_MS / 1000))
rms = librosa.feature.rms(y=y, frame_length=hop_length, hop_length=hop_length)[0]
median_window_frames = max(1, int(LOCAL_MEDIAN_WINDOW * sr / hop_length))
rms_padded = np.pad(rms, (median_window_frames//2,), mode='edge')
local_medians = np.convolve(rms_padded, np.ones(median_window_frames)/median_window_frames, mode='valid')
thresholds = local_medians * ADAPTIVE_THRESH_FACTOR

silent_sections = []
in_silence = False; start_time = 0
for i, (amp, thresh) in enumerate(zip(rms, thresholds)):
    time_sec = i * (hop_length / sr)
    if amp < thresh:
        if not in_silence: in_silence = True; start_time = time_sec
    else:
        if in_silence:
            end_time = time_sec
            if end_time - start_time >= MIN_SILENCE_LEN: silent_sections.append((start_time, end_time))
            in_silence = False

if in_silence:
    end_time = len(y) / sr
    if end_time - start_time >= MIN_SILENCE_LEN: silent_sections.append((start_time, end_time))

merged = []
for s, e in silent_sections:
    if merged and s - merged[-1][1] <= MERGE_CLOSE_SILENCES: merged[-1] = (merged[-1][0], e)
    else: merged.append((s, e))
silent_sections = merged

def snap_to_frame(time_sec, fps): return round(time_sec * fps) / fps
def seconds_to_smpte(sec, fps):
    total_frames = round(sec * fps)
    h = int(total_frames // (fps * 3600)); total_frames %= int(fps * 3600)
    m = int(total_frames // (fps * 60)); total_frames %= int(fps * 60)
    s = int(total_frames // fps); f = int(total_frames % fps)
    return f"{h:02d};{m:02d};{s:02d};{f:02d}"

silent_sections = [(snap_to_frame(s, FRAME_RATE), snap_to_frame(e, FRAME_RATE)) for s, e in silent_sections]
silent_smpte = [(seconds_to_smpte(s, FRAME_RATE), seconds_to_smpte(e, FRAME_RATE)) for s, e in silent_sections]

with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Start (SMPTE)", "End (SMPTE)"])
    writer.writerows(silent_smpte)

print(f"Detected {len(silent_smpte)} silent sections. Saved to: {OUTPUT_CSV}")
