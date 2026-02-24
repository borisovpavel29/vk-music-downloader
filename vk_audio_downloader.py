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

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests

VK_API_VERSION = "5.199"
VK_API_BASE = "https://api.vk.com/method"
CHUNK_SIZE = 64 * 1024

TRACK_PATTERN = re.compile(
    r"vk\.com/audio(?P<owner_id>-?\d+)_(?P<audio_id>\d+)(?:_(?P<access_key>[A-Za-z0-9]+))?"
)
PLAYLIST_PATTERN = re.compile(
    r"vk\.com/music/playlist/(?P<owner_id>-?\d+)_(?P<playlist_id>\d+)(?:_(?P<access_key>[A-Za-z0-9]+))?"
)
USER_AUDIO_PATTERN = re.compile(r"vk\.com/audios(?P<owner_id>-?\d+)")


class VkApiError(RuntimeError):
    """Raised on VK API errors."""


class HlsParseError(RuntimeError):
    """Raised when HLS playlist parsing fails."""


class MissingDependencyError(RuntimeError):
    """Raised when optional dependency is missing."""


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def sanitize_filename(name: str) -> str:
    sanitized = re.sub(r"[\\/:*?\"<>|]", "_", name).strip()
    sanitized = re.sub(r"\s+", " ", sanitized)
    return sanitized or "track"


def parse_track_url(url: str) -> Dict[str, Optional[str]]:
    match = TRACK_PATTERN.search(url)
    if not match:
        raise ValueError("Invalid track URL. Expected format: https://vk.com/audio<owner_id>_<audio_id>_<access_key>")
    return match.groupdict()


def parse_playlist_url(url: str) -> Dict[str, Optional[str]]:
    match = PLAYLIST_PATTERN.search(url)
    if not match:
        raise ValueError(
            "Invalid playlist URL. Expected format: https://vk.com/music/playlist/<owner_id>_<playlist_id>_<access_key>"
        )
    return match.groupdict()


def parse_user_audio_url(url: str) -> Dict[str, str]:
    match = USER_AUDIO_PATTERN.search(url)
    if not match:
        raise ValueError("Invalid user audio URL. Expected format: https://vk.com/audios<owner_id>")
    return {"owner_id": match.group("owner_id")}


def vk_api_call(method: str, token: str, params: Dict[str, object]) -> Dict[str, object]:
    request_params = dict(params)
    request_params["access_token"] = token
    request_params["v"] = VK_API_VERSION

    response = requests.get(f"{VK_API_BASE}/{method}", params=request_params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        error = data["error"]
        raise VkApiError(f"VK API error {error.get('error_code')}: {error.get('error_msg')}")

    return data["response"]


def get_track_info(token: str, owner_id: str, audio_id: str, access_key: Optional[str]) -> Dict[str, object]:
    audio_ref = f"{owner_id}_{audio_id}" + (f"_{access_key}" if access_key else "")
    response = vk_api_call("audio.getById", token, {"audios": audio_ref})
    if not response:
        raise RuntimeError("Track not found or inaccessible.")
    return response[0]


def get_playlist_tracks(
    token: str,
    owner_id: str,
    playlist_id: str,
    access_key: Optional[str],
) -> List[Dict[str, object]]:
    offset = 0
    count = 200
    all_tracks: List[Dict[str, object]] = []
    total_count: Optional[int] = None

    while True:
        params: Dict[str, object] = {
            "owner_id": owner_id,
            "album_id": playlist_id,
            "offset": offset,
            "count": count,
        }
        if access_key:
            params["access_key"] = access_key

        response = vk_api_call("audio.get", token, params)
        if total_count is None and isinstance(response, dict) and isinstance(response.get("count"), int):
            total_count = response["count"]

        items = response.get("items") if isinstance(response, dict) else None
        if not isinstance(items, list):
            items = []

        if not items:
            break

        all_tracks.extend(items)

        if len(items) < count:
            break

        offset += len(items)

        if total_count is not None and offset >= total_count:
            break

    if not all_tracks:
        raise RuntimeError("Playlist is empty, inaccessible, or VK API did not return items.")

    return all_tracks


def get_playlist_title(token: str, owner_id: str, playlist_id: str, access_key: Optional[str]) -> Optional[str]:
    params: Dict[str, object] = {"owner_id": owner_id, "playlist_ids": playlist_id}
    if access_key:
        params["access_key"] = access_key

    try:
        response = vk_api_call("audio.getPlaylists", token, params)
    except VkApiError as exc:
        logging.warning("Could not get playlist title: %s", exc)
        return None

    items = response.get("items") if isinstance(response, dict) else None
    if not isinstance(items, list) or not items:
        return None

    first_item = items[0]
    if isinstance(first_item, dict):
        title = first_item.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
    return None


def get_user_tracks(token: str, owner_id: str) -> List[Dict[str, object]]:
    offset = 0
    count = 200
    all_tracks: List[Dict[str, object]] = []
    total_count: Optional[int] = None

    while True:
        params: Dict[str, object] = {
            "owner_id": owner_id,
            "offset": offset,
            "count": count,
        }

        response = vk_api_call("audio.get", token, params)
        if total_count is None and isinstance(response, dict) and isinstance(response.get("count"), int):
            total_count = response["count"]

        items = response.get("items") if isinstance(response, dict) else None
        if not isinstance(items, list):
            items = []

        if not items:
            break

        all_tracks.extend(items)

        if len(items) < count:
            break

        offset += len(items)
        if total_count is not None and offset >= total_count:
            break

    if not all_tracks:
        raise RuntimeError("User audio is empty, inaccessible, or VK API did not return items.")

    return all_tracks


def download_file(url: str, destination: Path) -> None:
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with destination.open("wb") as file:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    file.write(chunk)


def parse_hls_attributes(line: str) -> Dict[str, str]:
    attributes: Dict[str, str] = {}
    for match in re.finditer(r'([A-Z0-9-]+)=((\"[^\"]*\")|[^,]+)', line):
        key = match.group(1)
        value = match.group(2).strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        attributes[key] = value
    return attributes


def maybe_unpad_pkcs7(data: bytes) -> bytes:
    if not data:
        return data
    pad_len = data[-1]
    if 1 <= pad_len <= 16 and data.endswith(bytes([pad_len]) * pad_len):
        return data[:-pad_len]
    return data


def parse_hls_segments(playlist_text: str, playlist_url: str) -> List[Dict[str, object]]:
    lines = [line.strip() for line in playlist_text.splitlines() if line.strip()]
    if not lines or lines[0] != "#EXTM3U":
        raise HlsParseError("Invalid HLS playlist content.")

    media_sequence = 0
    current_key: Dict[str, Optional[str]] = {"METHOD": None, "URI": None, "IV": None}
    segments: List[Dict[str, object]] = []
    stream_variants: List[Dict[str, object]] = []
    pending_stream_inf: Optional[Dict[str, str]] = None

    for line in lines:
        if line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            value = line.split(":", 1)[1]
            if value.isdigit():
                media_sequence = int(value)
        elif line.startswith("#EXT-X-STREAM-INF:"):
            pending_stream_inf = parse_hls_attributes(line.split(":", 1)[1])
        elif pending_stream_inf and not line.startswith("#"):
            variant = dict(pending_stream_inf)
            variant["URI"] = urljoin(playlist_url, line)
            stream_variants.append(variant)
            pending_stream_inf = None
        elif line.startswith("#EXT-X-KEY:"):
            attrs = parse_hls_attributes(line.split(":", 1)[1])
            current_key = {
                "METHOD": attrs.get("METHOD"),
                "URI": urljoin(playlist_url, attrs["URI"]) if attrs.get("URI") else None,
                "IV": attrs.get("IV"),
            }
        elif line.startswith("#"):
            continue
        else:
            segment_index = len(segments)
            segments.append(
                {
                    "url": urljoin(playlist_url, line),
                    "key": dict(current_key),
                    "sequence": media_sequence + segment_index,
                }
            )

    if stream_variants:
        stream_variants.sort(key=lambda v: int(v.get("BANDWIDTH", "0")), reverse=True)
        variant_url = stream_variants[0]["URI"]
        logging.info("HLS master playlist detected, using variant: %s", variant_url)
        response = requests.get(variant_url, timeout=30)
        response.raise_for_status()
        return parse_hls_segments(response.text, variant_url)

    if not segments:
        raise HlsParseError("No media segments found in HLS playlist.")

    return segments


def decrypt_hls_segment(data: bytes, key_bytes: bytes, iv_hex: Optional[str], sequence: int) -> bytes:
    try:
        from Crypto.Cipher import AES  # type: ignore
    except ModuleNotFoundError as exc:
        raise MissingDependencyError(
            "Missing dependency 'pycryptodome'. Install it with: pip install pycryptodome"
        ) from exc

    if iv_hex:
        normalized_iv = iv_hex[2:] if iv_hex.lower().startswith("0x") else iv_hex
        iv = bytes.fromhex(normalized_iv)
    else:
        iv = sequence.to_bytes(16, byteorder="big")

    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    return maybe_unpad_pkcs7(cipher.decrypt(data))


def download_hls(url: str, destination: Path) -> None:
    playlist_response = requests.get(url, timeout=30)
    playlist_response.raise_for_status()
    segments = parse_hls_segments(playlist_response.text, url)

    key_cache: Dict[str, bytes] = {}
    with destination.open("wb") as output_file:
        for segment in segments:
            segment_response = requests.get(str(segment["url"]), timeout=30)
            segment_response.raise_for_status()
            segment_data = segment_response.content

            key_data: Any = segment.get("key")
            if isinstance(key_data, dict) and key_data.get("METHOD") == "AES-128":
                key_uri = key_data.get("URI")
                if not key_uri:
                    raise HlsParseError("HLS segment is encrypted but key URI is missing.")
                if key_uri not in key_cache:
                    key_response = requests.get(str(key_uri), timeout=30)
                    key_response.raise_for_status()
                    key_cache[str(key_uri)] = key_response.content

                key_bytes = key_cache[str(key_uri)]
                segment_data = decrypt_hls_segment(
                    segment_data,
                    key_bytes,
                    key_data.get("IV") if isinstance(key_data.get("IV"), str) else None,
                    int(segment["sequence"]),
                )

            output_file.write(segment_data)


def is_hls_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return ".m3u8" in path


def track_to_filename(track: Dict[str, object], include_artist: bool = True) -> str:
    artist = str(track.get("artist") or "Unknown Artist")
    title = str(track.get("title") or "Unknown Title")
    if include_artist:
        return sanitize_filename(f"{artist} - {title}.mp3")
    return sanitize_filename(f"{title}.mp3")


def build_track_output_path(track: Dict[str, object], base_output_dir: Path, sort_mode: str) -> Path:
    artist = sanitize_filename(str(track.get("artist") or "Unknown Artist"))
    if sort_mode == "artist-folder":
        return base_output_dir / artist / track_to_filename(track, include_artist=False)
    if sort_mode == "artist-folder-name":
        return base_output_dir / artist / track_to_filename(track, include_artist=True)
    return base_output_dir / track_to_filename(track, include_artist=True)


def convert_to_mp3(source_path: Path, destination_path: Path) -> None:
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise MissingDependencyError("ffmpeg is required for HLS conversion to mp3. Install ffmpeg and try again.")

    commands = [
        [ffmpeg_path, "-y", "-i", str(source_path), "-vn", "-c:a", "libmp3lame", "-q:a", "2", str(destination_path)],
        [ffmpeg_path, "-y", "-i", str(source_path), "-vn", "-c:a", "mp3", str(destination_path)],
    ]
    last_error = ""
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            return
        last_error = (result.stderr or result.stdout).strip()

    raise RuntimeError(f"ffmpeg conversion failed: {last_error or 'unknown ffmpeg error'}")


def append_skipped_track(skipped_file: Path, track_output_path: Path) -> None:
    skipped_file.parent.mkdir(parents=True, exist_ok=True)
    with skipped_file.open("a", encoding="utf-8") as file:
        file.write(f"{track_output_path.name}\n")


def download_tracks_with_skip_log(
    tracks: List[Dict[str, object]],
    output_dir: Path,
    if_exists: str,
    sort_mode: str,
) -> None:
    skipped_file = output_dir / "_skipped.txt"
    skipped_count = 0

    for track in tracks:
        track_output_path = build_track_output_path(track, output_dir, sort_mode)
        try:
            result = download_track(track, output_dir, if_exists, sort_mode)
            if result is None:
                append_skipped_track(skipped_file, track_output_path)
                skipped_count += 1
        except (requests.RequestException, MissingDependencyError, RuntimeError, ValueError) as exc:
            logging.error("Track failed and will be skipped: %s (%s)", track_output_path.name, exc)
            append_skipped_track(skipped_file, track_output_path)
            skipped_count += 1

    if skipped_count > 0:
        logging.warning("Skipped tracks written to: %s (count: %d)", skipped_file.resolve(), skipped_count)


def download_track(track: Dict[str, object], output_dir: Path, if_exists: str, sort_mode: str) -> Optional[Path]:
    title = f"{track.get('artist', 'Unknown Artist')} - {track.get('title', 'Unknown Title')}"
    url = track.get("url")

    if not url:
        logging.warning("Skipping track without download URL: %s", title)
        return None

    hls_mode = is_hls_url(str(url))
    output_path = build_track_output_path(track, output_dir, sort_mode)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        if if_exists == "skip":
            logging.info("Track already exists, skipping: %s (%s)", title, output_path.resolve())
            return output_path

        logging.info("Track already exists, replacing: %s (%s)", title, output_path.resolve())

    logging.info("Track download started: %s", title)
    if hls_mode:
        logging.info("HLS stream detected for track: %s", title)
        temp_ts_path = output_path.with_suffix(".ts.tmp")
        try:
            download_hls(str(url), temp_ts_path)
            logging.info("Converting to mp3: %s", title)
            convert_to_mp3(temp_ts_path, output_path)
        finally:
            if temp_ts_path.exists():
                temp_ts_path.unlink()
    else:
        download_file(str(url), output_path)
    logging.info("Track file saved: %s", output_path.resolve())

    return output_path


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
    return parser


def main() -> int:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()

    if not args.token:
        parser.error("VK token is required. Pass --token or set VK_TOKEN environment variable.")

    output_dir = Path(args.path).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if args.track:
            parsed = parse_track_url(args.track)
            track = get_track_info(args.token, parsed["owner_id"], parsed["audio_id"], parsed.get("access_key"))
            download_track(track, output_dir, args.if_exists, args.sort)
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
            download_tracks_with_skip_log(tracks, output_dir, args.if_exists, args.sort)
        else:
            parsed = parse_user_audio_url(args.user)
            tracks = get_user_tracks(args.token, parsed["owner_id"])
            logging.info("User audio tracks received: %d", len(tracks))
            download_tracks_with_skip_log(tracks, output_dir, args.if_exists, args.sort)

        logging.info("Download completed.")
        return 0
    except (ValueError, VkApiError, requests.RequestException, MissingDependencyError, RuntimeError) as exc:
        logging.error("Download failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
