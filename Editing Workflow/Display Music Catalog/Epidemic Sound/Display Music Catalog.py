#!/usr/bin/env python3
import sys
import os
import re

MUSIC_FOLDER = "/Users/mjvrmqz/Downloads/Video Editing Assets/Sound Design/Epidemic Sound/Music Collection"

def extract_chapters(text):
    chapters = {}
    current_chapter = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        chapter_match = re.match(r'Chapter\s+\d+', line)
        if chapter_match:
            current_chapter = chapter_match.group()
            chapters[current_chapter] = []
            continue
        song_match = re.match(r'[•*\-]\s*(.*?)\s*[–—-]', line)
        if song_match and current_chapter:
            chapters[current_chapter].append(song_match.group(1))
    return chapters

def find_folder_paths(song_names):
    found_paths = {}
    for song in song_names:
        matches = []
        for root, dirs, files in os.walk(MUSIC_FOLDER):
            for dir_name in dirs:
                if dir_name.lower() == song.lower():
                    matches.append(os.path.join(root, dir_name))
        if matches:
            found_paths[song] = matches
        else:
            found_paths[song] = ["No match found"]
    return found_paths

def main():
    input_text = sys.stdin.read()
    chapters = extract_chapters(input_text)

    for chapter, songs in chapters.items():
        print(chapter)
        paths = find_folder_paths(songs)
        for song, matches in paths.items():
            print(f"  {song}:")
            for match in matches:
                print(f"    {match}")
        print()  # blank line between chapters

if __name__ == "__main__":
    main()
