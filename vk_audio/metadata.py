from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter

from get_metadata import get_source_order, lookup_metadata

from .errors import MissingDependencyError


def ensure_mutagen_available() -> None:
    try:
        import mutagen  # type: ignore  # noqa: F401
    except ModuleNotFoundError as exc:
        raise MissingDependencyError(
            "Missing dependency 'mutagen'. Install it with: pip install mutagen"
        ) from exc


class MetadataEnricher:
    """Fetches track metadata from external sources and writes ID3 tags."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.source_order = get_source_order(source)
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "vk-audio-downloader/1.0 (https://github.com/)"}
        )
        adapter = HTTPAdapter(max_retries=0)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self._last_request_at_by_source: Dict[str, float] = {}
        self._consecutive_network_failures: Dict[str, int] = {}
        self._disabled_sources: set[str] = set()
        self._last_metadata_source = "filename"

    def enrich_mp3(self, file_path: Path, track: Dict[str, object]) -> None:
        metadata = self.lookup(track)
        if not metadata:
            metadata = self.metadata_from_filename(file_path)
            self._last_metadata_source = "filename"
        if not metadata:
            return

        from mutagen.easyid3 import EasyID3  # type: ignore
        from mutagen.id3 import ID3NoHeaderError  # type: ignore
        from mutagen.mp3 import MP3  # type: ignore

        try:
            tags = EasyID3(str(file_path))
        except ID3NoHeaderError:
            audio_file = MP3(str(file_path))
            audio_file.add_tags()
            audio_file.save()
            tags = EasyID3(str(file_path))

        if metadata.get("title"):
            tags["title"] = [str(metadata["title"])]
        if metadata.get("artist"):
            tags["artist"] = [str(metadata["artist"])]
            tags["albumartist"] = [str(metadata["artist"])]
        if metadata.get("album"):
            tags["album"] = [str(metadata["album"])]
        if metadata.get("date"):
            tags["date"] = [str(metadata["date"])]
        if metadata.get("genre"):
            tags["genre"] = [str(metadata["genre"])]

        tags.save()
        logging.info("Metadata updated from %s: %s", self._last_metadata_source, file_path.name)

    def metadata_from_filename(self, file_path: Path) -> Optional[Dict[str, str]]:
        stem = file_path.stem.strip()
        if not stem:
            return None

        if " - " in stem:
            artist, title = stem.split(" - ", 1)
            artist = artist.strip()
            title = title.strip()
            if artist and title:
                return {"artist": artist, "title": title}

        parent_artist = file_path.parent.name.strip()
        if parent_artist and parent_artist != ".":
            return {"artist": parent_artist, "title": stem}

        return {"title": stem}

    def lookup(self, track: Dict[str, object]) -> Optional[Dict[str, str]]:
        artist = str(track.get("artist") or "").strip()
        title = str(track.get("title") or "").strip()
        if not artist or not title:
            return None

        for source in self.source_order:
            if source in self._disabled_sources:
                continue
            try:
                metadata = lookup_metadata(
                    source=source,
                    artist=artist,
                    title=title,
                    request_json=self.request_json,
                )
            except requests.RequestException as exc:
                logging.warning("Metadata source %s failed for '%s - %s': %s", source, artist, title, exc)
                continue
            if metadata:
                self._last_metadata_source = source
                self._consecutive_network_failures[source] = 0
                return metadata
        return None

    def throttle(self, source: str) -> None:
        min_interval = 1.1
        elapsed = time.monotonic() - self._last_request_at_by_source.get(source, 0.0)
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

    def request_json(self, source: str, base_url: str, params: Dict[str, str]) -> Dict[str, Any]:
        full_url = requests.Request("GET", base_url, params=params).prepare().url or base_url

        max_attempts = 4
        retryable_statuses = {429, 500, 502, 503, 504}
        response: Optional[requests.Response] = None
        last_exc: Optional[requests.RequestException] = None

        for attempt in range(1, max_attempts + 1):
            self.throttle(source)
            try:
                response = self.session.get(base_url, params=params, timeout=30)
                self._last_request_at_by_source[source] = time.monotonic()
                if response.status_code in retryable_statuses and attempt < max_attempts:
                    wait_seconds = min(8, 2 ** (attempt - 1))
                    logging.warning(
                        "Metadata retry %d/%d for %s (HTTP %d): %s",
                        attempt,
                        max_attempts - 1,
                        source,
                        response.status_code,
                        full_url,
                    )
                    time.sleep(wait_seconds)
                    continue
                response.raise_for_status()
                break
            except requests.RequestException as exc:
                self._last_request_at_by_source[source] = time.monotonic()
                last_exc = exc
                if attempt < max_attempts:
                    wait_seconds = min(8, 2 ** (attempt - 1))
                    logging.warning(
                        "Metadata retry %d/%d for %s after error: %s (%s)",
                        attempt,
                        max_attempts - 1,
                        source,
                        full_url,
                        exc,
                    )
                    time.sleep(wait_seconds)
                    continue
                failures = self._consecutive_network_failures.get(source, 0) + 1
                self._consecutive_network_failures[source] = failures
                if failures >= 3:
                    self._disabled_sources.add(source)
                    logging.warning(
                        "Metadata source %s disabled after %d consecutive network failures.",
                        source,
                        failures,
                    )
                raise

        if response is None:
            if last_exc is not None:
                raise last_exc
            return {}

        return response.json()
