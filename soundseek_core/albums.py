"""Группировка треков в альбомы.

Альбомы двух видов:

1. типовые — все треки, разложенные по ``derived.content_type``;
2. обычные — треки, у которых совпадают метаданные альбома и, если он указан,
   исполнитель альбома. Обычный альбом показывается только при наличии
   минимум двух треков.

Группировка не зависит от Gradio и легко тестируется отдельно.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha1

from .models import Track

CONTENT_TYPE_ORDER = (
    "music",
    "speech",
    "singing",
    "nature",
    "animal",
    "sound_effect",
    "noise",
    "unknown",
)


@dataclass
class Album:
    key: str
    kind: str
    title: str
    tracks: list[Track]
    artist: str = ""
    cover_path: str = ""
    content_type: str = ""

    @property
    def track_count(self) -> int:
        return len(self.tracks)


def _track_order(track: Track) -> tuple[int, int, str]:
    disc = track.tags.disc_number or 0
    number = track.tags.track_number or 10**6
    return disc, number, track.display_title.casefold()


def _type_sort_key(content_type: str) -> tuple[int, str]:
    try:
        return CONTENT_TYPE_ORDER.index(content_type), ""
    except ValueError:
        return len(CONTENT_TYPE_ORDER), content_type.casefold()


def build_type_albums(tracks: list[Track]) -> list[Album]:
    groups: dict[str, list[Track]] = defaultdict(list)
    for track in tracks:
        content_type = (track.derived.content_type or "unknown").strip() or "unknown"
        groups[content_type].append(track)

    albums = []
    for content_type in sorted(groups, key=_type_sort_key):
        items = sorted(groups[content_type], key=_track_order)
        albums.append(
            Album(
                key=f"type:{content_type}",
                kind="type",
                title=content_type,
                tracks=items,
                content_type=content_type,
            )
        )
    return albums


def build_metadata_albums(tracks: list[Track]) -> list[Album]:
    groups: dict[tuple[str, str], list[Track]] = defaultdict(list)
    for track in tracks:
        album = track.tags.album.strip()
        if not album:
            continue
        album_artist = track.tags.album_artist.strip()
        groups[(album.casefold(), album_artist.casefold())].append(track)

    albums = []
    for (album_norm, album_artist_norm), items in groups.items():
        if len(items) < 2:
            continue

        title = Counter(
            track.tags.album.strip() for track in items if track.tags.album.strip()
        ).most_common(1)[0][0]
        album_artist = next(
            (
                track.tags.album_artist.strip()
                for track in items
                if track.tags.album_artist.strip()
            ),
            "",
        )
        artists = {
            track.tags.artist.strip()
            for track in items
            if track.tags.artist.strip()
        }
        if album_artist:
            artist = album_artist
        elif len(artists) == 1:
            artist = next(iter(artists))
        elif artists:
            artist = "Разные исполнители"
        else:
            artist = ""

        cover_path = next(
            (
                track.tags.cover_path
                for track in items
                if track.tags.cover_path
            ),
            "",
        )
        digest = sha1(
            f"{album_norm}\0{album_artist_norm}".encode("utf-8")
        ).hexdigest()[:12]
        albums.append(
            Album(
                key=f"album:{digest}",
                kind="metadata",
                title=title,
                tracks=sorted(items, key=_track_order),
                artist=artist,
                cover_path=cover_path,
            )
        )

    return sorted(
        albums,
        key=lambda album: (album.title.casefold(), album.artist.casefold()),
    )


def build_album_sections(tracks: list[Track]) -> tuple[list[Album], list[Album]]:
    return build_type_albums(tracks), build_metadata_albums(tracks)
