from __future__ import annotations

import re
from typing import Dict, Optional


def normalize_for_match(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def build_metadata(
    *,
    title: str,
    artist: str,
    album: str = "",
    date: str = "",
    genre: str = "",
) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    if title.strip():
        metadata["title"] = title.strip()
    if artist.strip():
        metadata["artist"] = artist.strip()
    if album.strip():
        metadata["album"] = album.strip()
    if date.strip():
        metadata["date"] = date.strip()
    if genre.strip():
        metadata["genre"] = genre.strip()
    return metadata


def first_year(value: str) -> Optional[str]:
    match = re.search(r"\b(19|20)\d{2}\b", value or "")
    if not match:
        return None
    return match.group(0)
