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
    token = (env.get("DISCOGS_TOKEN") or "").strip()
    if not token:
        return None

    data = request_json(
        "discogs",
        "https://api.discogs.com/database/search",
        {
            "type": "release",
            "artist": artist,
            "track": title,
            "per_page": "10",
            "token": token,
        },
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

        display_title = str(item.get("title") or "")
        item_artist = artist
        item_track = title
        if " - " in display_title:
            split_artist, split_track = display_title.split(" - ", 1)
            if split_artist.strip() and split_track.strip():
                item_artist = split_artist.strip()
                item_track = split_track.strip()

        matched_title = normalize_for_match(item_track)
        matched_artist = normalize_for_match(item_artist)
        title_exact = int(matched_title == normalized_title)
        artist_match = int(
            normalized_artist in matched_artist or matched_artist in normalized_artist
        )
        rank = (title_exact, artist_match)
        if rank > best_rank:
            best_rank = rank
            best_item = item

    if not best_item:
        return None

    display_title = str(best_item.get("title") or "")
    result_artist = artist
    result_title = title
    if " - " in display_title:
        split_artist, split_track = display_title.split(" - ", 1)
        if split_artist.strip() and split_track.strip():
            result_artist = split_artist.strip()
            result_title = split_track.strip()

    year_value = best_item.get("year")
    date = str(year_value) if isinstance(year_value, int) and year_value > 0 else ""
    genre = ""
    genres = best_item.get("genre")
    if isinstance(genres, list) and genres:
        genre = str(genres[0] or "").strip()

    return build_metadata(
        title=result_title,
        artist=result_artist,
        date=date,
        genre=genre,
    )
