from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional

from . import deezer, discogs, itunes, lastfm, musicbrainz

LookupCallable = Callable[..., Optional[Dict[str, str]]]

LOOKUP_BY_SOURCE: Dict[str, LookupCallable] = {
    "itunes": itunes.lookup,
    "deezer": deezer.lookup,
    "musicbrainz": musicbrainz.lookup,
    "lastfm": lastfm.lookup,
    "discogs": discogs.lookup,
}

AUTO_SOURCES = ("itunes", "deezer", "musicbrainz", "lastfm", "discogs")
ALL_SOURCES = tuple(LOOKUP_BY_SOURCE.keys())


def get_source_order(source: str) -> list[str]:
    if source == "auto":
        return list(AUTO_SOURCES)
    return [source]


def lookup_metadata(
    *,
    source: str,
    artist: str,
    title: str,
    request_json: Callable[[str, str, Dict[str, str]], Dict[str, Any]],
) -> Optional[Dict[str, str]]:
    lookup_fn = LOOKUP_BY_SOURCE.get(source)
    if not lookup_fn:
        return None
    return lookup_fn(
        artist=artist,
        title=title,
        request_json=request_json,
        env=os.environ,
    )
