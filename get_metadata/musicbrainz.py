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
        "musicbrainz",
        "https://musicbrainz.org/ws/2/recording",
        {
            "fmt": "json",
            "limit": "5",
            "query": f'recording:"{title}" AND artist:"{artist}"',
        },
    )

    recordings = data.get("recordings")
    if not isinstance(recordings, list) or not recordings:
        return None

    normalized_title = normalize_for_match(title)
    normalized_artist = normalize_for_match(artist)

    best_recording: Optional[Dict[str, Any]] = None
    best_rank = (-1, -1, -1)
    for recording in recordings:
        if not isinstance(recording, dict):
            continue
        recording_title = str(recording.get("title") or "")
        artist_credit = recording.get("artist-credit") or []
        artist_credit_names = " ".join(
            str(item.get("name") or "") for item in artist_credit if isinstance(item, dict)
        )

        normalized_recording_title = normalize_for_match(recording_title)
        normalized_credit = normalize_for_match(artist_credit_names)

        title_exact = int(normalized_recording_title == normalized_title)
        artist_match = int(
            normalized_artist in normalized_credit or normalized_credit in normalized_artist
        )
        score = int(recording.get("score") or 0)
        rank = (title_exact, artist_match, score)
        if rank > best_rank:
            best_rank = rank
            best_recording = recording

    if not best_recording:
        return None

    release_list = best_recording.get("releases")
    release = release_list[0] if isinstance(release_list, list) and release_list else {}
    album = str(release.get("title") or "").strip() if isinstance(release, dict) else ""
    date = str(release.get("date") or "").strip() if isinstance(release, dict) else ""

    tags = best_recording.get("tags")
    genre = ""
    if isinstance(tags, list) and tags and isinstance(tags[0], dict):
        genre = str(tags[0].get("name") or "").strip()

    return build_metadata(
        title=str(best_recording.get("title") or title),
        artist=artist,
        album=album,
        date=date,
        genre=genre,
    )
