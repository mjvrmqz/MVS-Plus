import ffmpeg
import sys
import os

# Usage:
# python convert_to_dnxhr.py /path/to/file1.mp4 /path/to/file2.mov

input_files = sys.argv[1:]

if not input_files:
    sys.exit(0)

for file_path in input_files:
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        continue

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_file = os.path.join(os.path.dirname(file_path), f"{base_name}_DNXHR.mov")

    try:
        print(f"Converting {file_path} → {output_file}")
        (
            ffmpeg
            .input(file_path)
            .output(
                output_file,
                vcodec='dnxhd',
                acodec='pcm_s16le',
                movflags='faststart'
            )
            .overwrite_output()
            .run()
        )
        print(f"Finished: {output_file}")

        os.remove(file_path)
        print(f"Deleted original: {file_path}")

    except ffmpeg.Error as e:
        print(f"Failed to convert {file_path}: {e}")