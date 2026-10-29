"""HTML-представление вкладки «Альбомы»."""

from __future__ import annotations

import base64
import mimetypes
from functools import lru_cache
from html import escape
from pathlib import Path

from soundseek_core.albums import Album
from soundseek_core.models import Track
from web_app.player_ui import play_button_html

PALETTE = [
    "#2563eb",
    "#dc2626",
    "#16a34a",
    "#d97706",
    "#7c3aed",
    "#0891b2",
    "#be185d",
    "#65a30d",
    "#b45309",
    "#4338ca",
    "#0f766e",
    "#a21caf",
]

TYPE_META = {
    "music": ("Музыка", "♪", "#2563eb"),
    "speech": ("Речь и разговоры", "💬", "#0f766e"),
    "singing": ("Вокал", "♫", "#be185d"),
    "nature": ("Природа", "❧", "#16a34a"),
    "animal": ("Животные", "🐾", "#b45309"),
    "sound_effect": ("Звуковые эффекты", "◇", "#7c3aed"),
    "noise": ("Шум", "≋", "#64748b"),
    "unknown": ("Не определено", "?", "#475569"),
}


def _plural(number: int, one: str, few: str, many: str) -> str:
    tail = number % 100
    if 11 <= tail <= 19:
        return many
    last = number % 10
    if last == 1:
        return one
    if 2 <= last <= 4:
        return few
    return many


def _tracks_label(number: int) -> str:
    return f"{number} {_plural(number, 'трек', 'трека', 'треков')}"


def _albums_label(number: int) -> str:
    return f"{number} {_plural(number, 'альбом', 'альбома', 'альбомов')}"


def _humanize_content_type(value: str) -> str:
    return (value or "unknown").replace("_", " ").strip().capitalize()


def _type_meta(value: str) -> tuple[str, str, str]:
    return TYPE_META.get(
        value,
        (_humanize_content_type(value), "♪", _accent_for(value)),
    )


def _accent_for(text: str) -> str:
    checksum = sum((index + 1) * ord(char) for index, char in enumerate(text))
    return PALETTE[checksum % len(PALETTE)]


@lru_cache(maxsize=256)
def _cover_data_uri_cached(path: str, _mtime_ns: int) -> str:
    file_path = Path(path)
    mime = mimetypes.guess_type(file_path.name)[0] or "image/jpeg"
    data = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def cover_data_uri(path: str) -> str:
    if not path:
        return ""
    file_path = Path(path)
    try:
        stat = file_path.stat()
        if not file_path.is_file():
            return ""
        return _cover_data_uri_cached(str(file_path), stat.st_mtime_ns)
    except OSError:
        return ""


def _cover_html(album: Album) -> str:
    if album.kind == "metadata":
        uri = cover_data_uri(album.cover_path)
        if uri:
            alt = escape(f"Обложка альбома {album.title}", quote=True)
            return (
                f'<img src="{uri}" alt="{alt}" loading="lazy" />'
            )
        initial = escape((album.title.strip()[:1] or "?").upper())
        accent = _accent_for(album.title)
        return (
            '<div class="soundseek-album-placeholder '
            'soundseek-album-placeholder-letter" '
            f'style="--album-accent:{accent}">'
            f"<span>{initial}</span></div>"
        )

    label, glyph, accent = _type_meta(album.content_type)
    return (
        '<div class="soundseek-album-placeholder '
        'soundseek-album-placeholder-type" '
        f'style="--album-accent:{accent}">'
        f'<span class="soundseek-album-glyph">{escape(glyph)}</span>'
        f'<span class="soundseek-album-placeholder-label">{escape(label)}</span>'
        "</div>"
    )


def _album_meta(album: Album) -> str:
    if album.kind == "type":
        return f"Тип контента · {_tracks_label(album.track_count)}"
    parts = [album.artist] if album.artist else []
    parts.append(_tracks_label(album.track_count))
    return " · ".join(parts)


def _album_title(album: Album) -> str:
    if album.kind == "type":
        return _type_meta(album.content_type)[0]
    return album.title


def _album_card(album: Album) -> str:
    title = _album_title(album)
    meta = _album_meta(album)
    escaped_title = escape(title)
    escaped_meta = escape(meta)
    aria = escape(f"{title} — {meta}", quote=True)
    return (
        '<button type="button" class="soundseek-album-card" '
        f'data-album-key="{escape(album.key, quote=True)}" '
        f'aria-label="{aria}">'
        '<div class="soundseek-album-cover">'
        f"{_cover_html(album)}"
        "</div>"
        '<div class="soundseek-album-caption">'
        f'<div class="soundseek-album-title" title="{escaped_title}">'
        f"{escaped_title}</div>"
        f'<div class="soundseek-album-meta">{escaped_meta}</div>'
        "</div>"
        "</button>"
    )


def _section(
    title: str,
    subtitle: str,
    albums: list[Album],
    empty_text: str,
) -> str:
    if albums:
        cards = "".join(_album_card(album) for album in albums)
        body = f'<div class="soundseek-album-grid">{cards}</div>'
    else:
        body = (
            '<div class="soundseek-albums-empty">'
            f"{escape(empty_text)}</div>"
        )
    return (
        '<section class="soundseek-albums-section">'
        '<div class="soundseek-albums-heading">'
        "<div>"
        f'<div class="soundseek-albums-kicker">{escape(subtitle)}</div>'
        f'<h3 class="soundseek-albums-title">{escape(title)}</h3>'
        "</div>"
        f'<div class="soundseek-albums-count">'
        f"{_albums_label(len(albums))}</div>"
        "</div>"
        f"{body}"
        "</section>"
    )


def build_albums_view(
    type_albums: list[Album],
    metadata_albums: list[Album],
) -> str:
    if not type_albums and not metadata_albums:
        return (
            '<div class="soundseek-warning-card soundseek-albums-empty">'
            "В библиотеке пока нет треков для альбомов."
            "</div>"
        )
    return (
        '<div class="soundseek-albums-page">'
        + _section(
            "По типам контента",
            "Основные альбомы",
            type_albums,
            "Нет треков с определённым типом контента.",
        )
        + _section(
            "Альбомы из метаданных",
            "Два трека и больше",
            metadata_albums,
            "Пока нет альбомов, в которых минимум два трека "
            "с одинаковыми метаданными.",
        )
        + "</div>"
    )


def _duration_label(seconds: float) -> str:
    if not seconds or seconds <= 0:
        return "—"
    total = int(round(seconds))
    return f"{total // 60}:{total % 60:02d}"


def _track_row(index: int, track: Track) -> str:
    title = escape(track.display_title)
    artist = escape(track.tags.artist or "—")
    details = [artist]
    if track.derived.genre:
        details.append(escape(track.derived.genre))
    if track.derived.mood:
        details.append(escape(track.derived.mood))
    meta = " · ".join(details)
    duration = _duration_label(track.derived.duration)
    return (
        '<li class="soundseek-album-track">'
        f'<span class="soundseek-album-track-number">{index:02d}</span>'
        f"{play_button_html(track.id, track.display_title)}"
        '<span class="soundseek-album-track-copy">'
        f'<span class="soundseek-album-track-title">{title}</span>'
        f'<span class="soundseek-album-track-meta">{meta}</span>'
        "</span>"
        f'<span class="soundseek-album-track-duration">{duration}</span>'
        "</li>"
    )


def format_album_detail(album: Album | None) -> str:
    if album is None:
        return (
            '<div class="soundseek-album-detail soundseek-light-card '
            'soundseek-album-detail-empty">'
            '<div class="soundseek-album-detail-kicker">Альбомы</div>'
            '<div class="soundseek-album-detail-title">Выберите альбом</div>'
            '<div class="soundseek-album-detail-meta">'
            "Нажмите на обложку — здесь появятся треки."
            "</div></div>"
        )

    title = escape(_album_title(album))
    meta = escape(_album_meta(album))
    kind = "Тип контента" if album.kind == "type" else "Альбом"
    rows = "".join(
        _track_row(index, track)
        for index, track in enumerate(album.tracks, 1)
    )
    return (
        '<div class="soundseek-album-detail soundseek-light-card">'
        '<div class="soundseek-album-detail-head">'
        '<div class="soundseek-album-detail-cover">'
        f"{_cover_html(album)}"
        "</div>"
        '<div class="soundseek-album-detail-copy">'
        f'<div class="soundseek-album-detail-kicker">{kind}</div>'
        f'<div class="soundseek-album-detail-title">{title}</div>'
        f'<div class="soundseek-album-detail-meta">{meta}</div>'
        "</div>"
        "</div>"
        f'<ol class="soundseek-album-tracklist">{rows}</ol>'
        "</div>"
    )
