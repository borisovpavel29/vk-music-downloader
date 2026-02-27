from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .common import build_metadata, normalize_for_match


def lookup(
    *,
    artist: str,
    title: str,
    request_json: Callable[[str, str, Dict[str, str]], Dict[str, Any]],
    env: Dict[str, str],
) -> Optional[Dict[str, str]]:
    data = request_json(
        "deezer",
        "https://api.deezer.com/search",
        {"q": f'artist:"{artist}" track:"{title}"', "limit": "10"},
    )

    items = data.get("data")
    if not isinstance(items, list) or not items:
        return None

    normalized_title = normalize_for_match(title)
    normalized_artist = normalize_for_match(artist)
    best_item: Optional[Dict[str, Any]] = None
    best_rank = (-1, -1)

    for item in items:
        if not isinstance(item, dict):
            continue
        item_title = normalize_for_match(str(item.get("title") or ""))
        artist_data = item.get("artist") or {}
        item_artist_raw = str(artist_data.get("name") or "") if isinstance(artist_data, dict) else ""
        item_artist = normalize_for_match(item_artist_raw)
        title_exact = int(item_title == normalized_title)
        artist_match = int(
            normalized_artist in item_artist or item_artist in normalized_artist
        )
        rank = (title_exact, artist_match)
        if rank > best_rank:
            best_rank = rank
            best_item = item

    if not best_item:
        return None

    artist_data = best_item.get("artist") or {}
    album_data = best_item.get("album") or {}
    return build_metadata(
        title=str(best_item.get("title") or title),
        artist=str(artist_data.get("name") or artist) if isinstance(artist_data, dict) else artist,
        album=str(album_data.get("title") or "") if isinstance(album_data, dict) else "",
    )
