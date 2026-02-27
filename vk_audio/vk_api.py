from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

import requests

from .errors import VkApiError

VK_API_VERSION = "5.199"
VK_API_BASE = "https://api.vk.com/method"

TRACK_PATTERN = re.compile(
    r"vk\.com/audio(?P<owner_id>-?\d+)_(?P<audio_id>\d+)(?:_(?P<access_key>[A-Za-z0-9]+))?"
)
PLAYLIST_PATTERN = re.compile(
    r"vk\.com/music/playlist/(?P<owner_id>-?\d+)_(?P<playlist_id>\d+)(?:_(?P<access_key>[A-Za-z0-9]+))?"
)
USER_AUDIO_PATTERN = re.compile(r"vk\.com/audios(?P<owner_id>-?\d+)")


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
