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
        "itunes",
        "https://itunes.apple.com/search",
        {"term": f"{artist} {title}", "entity": "song", "limit": "10"},
    )

    results = data.get("results")
    if not isinstance(results, list) or not results:
        return None

    normalized_title = normalize_for_match(title)
    normalized_artist = normalize_for_match(artist)
    best_item: Optional[Dict[str, Any]] = None
    best_rank = (-1, -1)

    for item in results:
        if not isinstance(item, dict):
            continue
        item_title = normalize_for_match(str(item.get("trackName") or ""))
        item_artist = normalize_for_match(str(item.get("artistName") or ""))
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

    release_date = str(best_item.get("releaseDate") or "")
    release_date = release_date[:10] if release_date else ""

    return build_metadata(
        title=str(best_item.get("trackName") or title),
        artist=str(best_item.get("artistName") or artist),
        album=str(best_item.get("collectionName") or ""),
        date=release_date,
        genre=str(best_item.get("primaryGenreName") or ""),
    )
