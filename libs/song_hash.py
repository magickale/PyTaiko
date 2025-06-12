import json
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from libs.tja import TJAParser
from libs.utils import get_config

song_hashes: Optional[dict] = None


def process_tja_file(tja_file):
    """Process a single TJA file and return hash or None if error"""
    tja = TJAParser(tja_file)
    all_notes = []
    for diff in tja.metadata.course_data:
        all_notes.extend(
            TJAParser.notes_to_position(TJAParser(tja.file_path), diff)
        )
    hash = tja.hash_note_data(all_notes[0], all_notes[2])
    return hash


def build_song_hashes(output_file="cache/song_hashes.json"):
    existing_hashes = {}
    output_path = Path(output_file)
    if output_path.exists():
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                existing_hashes = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(
                f"Warning: Could not load existing hashes from {output_file}: {e}"
            )
            existing_hashes = {}

    song_hashes = existing_hashes.copy()
    tja_paths = get_config()["paths"]["tja_path"]
    all_tja_files = []

    for root_dir in tja_paths:
        root_path = Path(root_dir)
        all_tja_files.extend(root_path.rglob("*.tja"))

    updated_count = 0
    for tja_file in all_tja_files:
        current_modified = tja_file.stat().st_mtime

        should_update = False
        hash_val = None

        existing_hash = None
        for h, data in song_hashes.items():
            if data["file_path"] == str(tja_file):
                existing_hash = h
                break

        if existing_hash is None:
            should_update = True
        else:
            stored_modified = song_hashes[existing_hash].get("last_modified", 0)
            if current_modified > stored_modified:
                should_update = True
                del song_hashes[existing_hash]

        if should_update:
            tja = TJAParser(tja_file)
            all_notes = []
            for diff in tja.metadata.course_data:
                all_notes.extend(
                    TJAParser.notes_to_position(TJAParser(tja.file_path), diff)
                )
            hash_val = tja.hash_note_data(all_notes[0], all_notes[2])
            song_hashes[hash_val] = {
                "file_path": str(tja_file),
                "last_modified": current_modified,
                "title": tja.metadata.title,
                "subtitle": tja.metadata.subtitle,
            }
            updated_count += 1

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(song_hashes, f, indent=2, ensure_ascii=False)

    print(f"Song hashes saved to {output_file}. Updated {updated_count} files.")
    return song_hashes


def get_japanese_songs_for_version(df, version_column):
    # Filter rows where the specified version column has 'YES'
    version_songs = df[df[version_column] != "NO"]

    # Extract Japanese titles (JPTITLE column)
    japanese_titles = version_songs[
        "TITLE 【TITLE2】\nJPTITLE／「TITLE2」 より"
    ].tolist()

    japanese_titles = [name.split("\n") for name in japanese_titles]
    second_lines = [
        name[1] if len(name) > 1 else name[0] for name in japanese_titles
    ]

    all_tja_files = []
    direct_tja_paths = dict()
    text_files = dict()
    tja_paths = get_config()["paths"]["tja_path"]
    for root_dir in tja_paths:
        root_path = Path(root_dir)
        all_tja_files.extend(root_path.rglob("*.tja"))
    for tja in all_tja_files:
        tja_parse = TJAParser(tja)
        tja_name = tja_parse.metadata.title.get(
            "ja", tja_parse.metadata.title["en"]
        )
        if "【双打】" in tja_name:
            tja_name = tja_name.strip("【双打】")
            tja_name = tja_name.strip()
        if tja_name in direct_tja_paths:
            direct_tja_paths[tja_name].append(tja)
        else:
            direct_tja_paths[tja_name] = [tja]
    for title in second_lines:
        if "・・・" in title:
            title = title.replace("・・・", "…")
        if "..." in title:
            title = title.replace("・・・", "…")

        # Find all matching keys
        matches = []

        # Check for exact title match
        if title in direct_tja_paths:
            for path in direct_tja_paths[title]:
                matches.append((title, path))

        # Also check for partial matches with the first part before '／'
        title_prefix = title.split("／")[0]
        for key in direct_tja_paths:
            if key.startswith(title_prefix) and key != title:
                for path in direct_tja_paths[key]:
                    matches.append((key, path))

        if not matches:
            for key in direct_tja_paths:
                if title.lower() in key.lower() or key.lower() in title.lower():
                    for path in direct_tja_paths[key]:
                        matches.append((key, path))

        if not matches:
            from difflib import get_close_matches

            close_matches = get_close_matches(
                title, direct_tja_paths.keys(), n=3, cutoff=0.6
            )
            for close_match in close_matches:
                for path in direct_tja_paths[close_match]:
                    matches.append((close_match, path))

        if len(matches) == 1:
            path = matches[0][1]
        elif len(matches) > 1:
            print(
                f"Multiple matches found for '{title.split('／')[0]} ({title.split('／')[1] if len(title.split('／')) > 1 else ''})':"
            )
            for i, (key, path_val) in enumerate(matches, 1):
                print(f"{i}. {key}: {path_val}")
            choice = int(input("Choose number: ")) - 1
            path = matches[choice][1]
        else:
            path = Path(input(f"NOT FOUND {title}: "))
        hash = process_tja_file(path)
        tja_parse = TJAParser(Path(path))
        genre = Path(path).parent.parent.name
        if genre not in text_files:
            text_files[genre] = []
        text_files[genre].append(
            f"{hash}|{tja_parse.metadata.title['en'].strip()}|{tja_parse.metadata.subtitle['en'].strip()}"
        )
        print(f"Added {title}: {path}")
    for genre in text_files:
        if not Path(version_column).exists():
            Path(version_column).mkdir()
        if not Path(f"{version_column}/{genre}").exists():
            Path(f"{version_column}/{genre}").mkdir()
        with open(
            Path(f"{version_column}/{genre}/song_list.txt"),
            "w",
            encoding="utf-8-sig",
        ) as text_file:
            for item in text_files[genre]:
                text_file.write(item + "\n")
    return text_files


if len(sys.argv) > 1:
    get_japanese_songs_for_version(pd.read_csv("full.csv"), sys.argv[1])
