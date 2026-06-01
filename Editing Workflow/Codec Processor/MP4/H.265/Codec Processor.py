import ffmpeg
import sys
import os

# Usage:
# python convert_to_hevc.py /path/to/file1.mov /path/to/file2.mp4

input_files = sys.argv[1:]

if not input_files:
    sys.exit(0)

for file_path in input_files:
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        continue

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_file = os.path.join(os.path.dirname(file_path), f"{base_name}_HEVC.mp4")

    try:
        print(f"Converting {file_path} → {output_file}")
        (
            ffmpeg
            .input(file_path)
            .output(
                output_file,
                vcodec='libx265',
                acodec='aac',
                audio_bitrate='192k',
                movflags='faststart',
                pix_fmt='yuv420p'
            )
            .overwrite_output()
            .run()
        )
        print(f"Finished: {output_file}")

        os.remove(file_path)
        print(f"Deleted original: {file_path}")

    except ffmpeg.Error as e:
        print(f"Failed to convert {file_path}: {e}")