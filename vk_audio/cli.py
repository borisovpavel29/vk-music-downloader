from __future__ import annotations

import argparse
import os

from get_metadata import ALL_SOURCES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download music from VK by track or playlist URL.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--track", help="VK track URL, e.g. https://vk.com/audio142774160_456240188_key")
    group.add_argument(
        "--playlist",
        help="VK playlist URL, e.g. https://vk.com/music/playlist/142774160_74879692_key",
    )
    group.add_argument("--user", help="VK user audio URL, e.g. https://vk.com/audios142774160")

    parser.add_argument("--path", default=".", help="Directory where audio files will be saved (default: current directory).")
    parser.add_argument("--token", default=os.getenv("VK_TOKEN"), help="VK API token (or set VK_TOKEN env var).")
    parser.add_argument(
        "--if-exists",
        choices=("skip", "replace"),
        default="skip",
        help="Behavior when target file already exists: skip or replace (default: skip).",
    )
    parser.add_argument(
        "--sort",
        choices=("none", "artist-folder", "artist-folder-name"),
        default="none",
        help="Output sorting mode: none, artist-folder, or artist-folder-name (default: none).",
    )
    parser.add_argument(
        "--metadata-source",
        choices=("none", "auto", *ALL_SOURCES),
        default="none",
        help="External metadata source for ID3 tags: none, auto, itunes, deezer, musicbrainz, lastfm, discogs (default: none).",
    )
    return parser

