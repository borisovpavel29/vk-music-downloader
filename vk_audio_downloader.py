#!/usr/bin/env python3
"""VK audio downloader CLI.

Usage examples:
  python vk_audio_downloader.py --track https://vk.com/audio142774160_456240188_71b76a487be610b2fb
  python vk_audio_downloader.py --playlist https://vk.com/music/playlist/142774160_74879692_d64ad4a8663b97a847 --path ./music
  python vk_audio_downloader.py --user https://vk.com/audios142774160 --path ./music

Authentication:
  Provide VK user token with audio access via --token or VK_TOKEN environment variable.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import requests

from vk_audio.cli import build_parser
from vk_audio.download import download_track, download_tracks_with_skip_log
from vk_audio.errors import MissingDependencyError, VkApiError
from vk_audio.metadata import MetadataEnricher, ensure_mutagen_available
from vk_audio.vk_api import (
    get_playlist_title,
    get_playlist_tracks,
    get_track_info,
    get_user_tracks,
    parse_playlist_url,
    parse_track_url,
    parse_user_audio_url,
)


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main() -> int:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()

    if not args.token:
        parser.error("VK token is required. Pass --token or set VK_TOKEN environment variable.")

    output_dir = Path(args.path).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata_enricher: MetadataEnricher | None = None
    if args.metadata_source != "none":
        ensure_mutagen_available()
        metadata_enricher = MetadataEnricher(args.metadata_source)

    try:
        if args.track:
            parsed = parse_track_url(args.track)
            track = get_track_info(args.token, parsed["owner_id"], parsed["audio_id"], parsed.get("access_key"))
            download_track(track, output_dir, args.if_exists, args.sort, metadata_enricher)
        elif args.playlist:
            parsed = parse_playlist_url(args.playlist)
            playlist_title = get_playlist_title(
                args.token,
                parsed["owner_id"],
                parsed["playlist_id"],
                parsed.get("access_key"),
            )
            if playlist_title:
                logging.info("Playlist title: %s", playlist_title)

            tracks = get_playlist_tracks(
                args.token,
                parsed["owner_id"],
                parsed["playlist_id"],
                parsed.get("access_key"),
            )
            logging.info("Playlist tracks received: %d", len(tracks))
            download_tracks_with_skip_log(tracks, output_dir, args.if_exists, args.sort, metadata_enricher)
        else:
            parsed = parse_user_audio_url(args.user)
            tracks = get_user_tracks(args.token, parsed["owner_id"])
            logging.info("User audio tracks received: %d", len(tracks))
            download_tracks_with_skip_log(tracks, output_dir, args.if_exists, args.sort, metadata_enricher)

        logging.info("Download completed.")
        return 0
    except (ValueError, VkApiError, requests.RequestException, MissingDependencyError, RuntimeError) as exc:
        logging.error("Download failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
