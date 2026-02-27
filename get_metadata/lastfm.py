from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .common import build_metadata, first_year


def lookup(
    *,
    artist: str,
    title: str,
    request_json: Callable[[str, str, Dict[str, str]], Dict[str, Any]],
    env: Dict[str, str],
) -> Optional[Dict[str, str]]:
    api_key = (env.get("LASTFM_API_KEY") or "").strip()
    if not api_key:
        return None

    data = request_json(
        "lastfm",
        "https://ws.audioscrobbler.com/2.0/",
        {
            "method": "track.getInfo",
            "artist": artist,
            "track": title,
            "api_key": api_key,
            "format": "json",
            "autocorrect": "1",
        },
    )

    track_data = data.get("track")
    if not isinstance(track_data, dict):
        return None

    album_data = track_data.get("album") or {}
    album_title = str(album_data.get("title") or "").strip() if isinstance(album_data, dict) else ""

    date = ""
    wiki_data = track_data.get("wiki") or {}
    if isinstance(wiki_data, dict):
        published = str(wiki_data.get("published") or "")
        year = first_year(published)
        if year:
            date = year

    genre = ""
    toptags = track_data.get("toptags") or {}
    if isinstance(toptags, dict):
        tags = toptags.get("tag")
        if isinstance(tags, list) and tags and isinstance(tags[0], dict):
            genre = str(tags[0].get("name") or "").strip()

    artist_name = track_data.get("artist")
    if isinstance(artist_name, dict):
        artist_name = artist_name.get("name")

    return build_metadata(
        title=str(track_data.get("name") or title),
        artist=str(artist_name or artist),
        album=album_title,
        date=date,
        genre=genre,
    )
