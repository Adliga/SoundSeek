"""Чтение тегов, обложек и встроенных текстов песен."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from mutagen import File as MutagenFile
from mutagen.flac import FLAC
from mutagen.id3 import APIC, ID3, SYLT, USLT
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4


def _extract_year(value) -> Optional[int]:
    if not value:
        return None
    if isinstance(value, int):
        return value
    text = str(value)
    for token in text.replace("-", " ").replace("/", " ").split():
        if token.isdigit() and len(token) == 4:
            return int(token)
    return None


def _extract_int(value) -> Optional[int]:
    if not value:
        return None
    if isinstance(value, (tuple, list)):
        value = value[0] if value else None
    text = str(value).split("/")[0].strip()
    return int(text) if text.isdigit() else None


def _first(value):
    if isinstance(value, list) and value:
        return value[0]
    return value


def _clean(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _read_mp3(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    try:
        audio = MP3(str(path), ID3=ID3)
        if audio.tags is None:
            return result
        tags = audio.tags
        result["title"] = _clean(tags.get("TIT2"))
        result["artist"] = _clean(tags.get("TPE1"))
        result["album"] = _clean(tags.get("TALB"))
        result["album_artist"] = _clean(tags.get("TPE2"))
        result["year"] = _extract_year(tags.get("TDRC") or tags.get("TYER"))
        result["track_number"] = _extract_int(tags.get("TRCK"))
        result["disc_number"] = _extract_int(tags.get("TPOS"))
        result["genre"] = _clean(tags.get("TCON"))
        result["composer"] = _clean(tags.get("TCOM"))
        result["comment"] = _clean(tags.get("COMM::eng") or tags.get("COMM"))

        for tag in tags.values():
            if isinstance(tag, APIC):
                result["_cover_data"] = tag.data
                result["_cover_mime"] = tag.mime
                break

        # USLT — обычный текст, SYLT — синхронизированный текст.
        for key in tags.keys():
            if key.startswith("USLT"):
                frame = tags.get(key)
                if isinstance(frame, USLT) and frame.text:
                    result["_lyrics"] = str(frame.text)
                    result["_lyrics_source"] = "id3:USLT"
                    break
        if "_lyrics" not in result:
            for key in tags.keys():
                if key.startswith("SYLT"):
                    frame = tags.get(key)
                    if isinstance(frame, SYLT) and frame.text:
                        lines = [text for _time, text in frame.text if text]
                        if lines:
                            result["_lyrics"] = "\n".join(lines)
                            result["_lyrics_source"] = "id3:SYLT"
                            break
    except Exception as exc:
        print(f"    mutagen MP3: {exc}")
    return result


def _read_flac(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    try:
        audio = FLAC(str(path))
        result["title"] = _first(audio.get("title")) or ""
        result["artist"] = _first(audio.get("artist")) or ""
        result["album"] = _first(audio.get("album")) or ""
        result["album_artist"] = _first(audio.get("albumartist")) or ""
        result["year"] = _extract_year(_first(audio.get("date")))
        result["track_number"] = _extract_int(_first(audio.get("tracknumber")))
        result["disc_number"] = _extract_int(_first(audio.get("discnumber")))
        result["genre"] = _first(audio.get("genre")) or ""
        result["composer"] = _first(audio.get("composer")) or ""
        result["comment"] = _first(audio.get("comment")) or ""
        lyrics = _first(audio.get("lyrics")) or _first(audio.get("unsyncedlyrics"))
        if lyrics:
            result["_lyrics"] = str(lyrics)
            result["_lyrics_source"] = "flac:LYRICS"
        if audio.pictures:
            picture = audio.pictures[0]
            result["_cover_data"] = picture.data
            result["_cover_mime"] = picture.mime
    except Exception as exc:
        print(f"    mutagen FLAC: {exc}")
    return result


def _read_mp4(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    try:
        audio = MP4(str(path))
        result["title"] = _first(audio.get("\xa9nam")) or ""
        result["artist"] = _first(audio.get("\xa9ART")) or ""
        result["album"] = _first(audio.get("\xa9alb")) or ""
        result["album_artist"] = _first(audio.get("aART")) or ""
        result["year"] = _extract_year(_first(audio.get("\xa9day")))
        result["track_number"] = _extract_int(_first(audio.get("trkn")))
        result["disc_number"] = _extract_int(_first(audio.get("disk")))
        result["genre"] = _first(audio.get("\xa9gen")) or ""
        result["composer"] = _first(audio.get("\xa9wrt")) or ""
        result["comment"] = _first(audio.get("\xa9cmt")) or ""
        lyrics = _first(audio.get("\xa9lyr"))
        if lyrics:
            result["_lyrics"] = str(lyrics)
            result["_lyrics_source"] = "mp4:©lyr"
        covers = audio.get("covr")
        if covers:
            result["_cover_data"] = bytes(covers[0])
            result["_cover_mime"] = "image/jpeg"
    except Exception as exc:
        print(f"    mutagen MP4: {exc}")
    return result


def _read_ogg(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    try:
        audio = MutagenFile(str(path))
        if audio is None or audio.tags is None:
            return result
        result["title"] = _first(audio.tags.get("title")) or ""
        result["artist"] = _first(audio.tags.get("artist")) or ""
        result["album"] = _first(audio.tags.get("album")) or ""
        result["album_artist"] = _first(audio.tags.get("albumartist")) or ""
        result["year"] = _extract_year(_first(audio.tags.get("date")))
        result["track_number"] = _extract_int(_first(audio.tags.get("tracknumber")))
        result["disc_number"] = _extract_int(_first(audio.tags.get("discnumber")))
        result["genre"] = _first(audio.tags.get("genre")) or ""
        result["composer"] = _first(audio.tags.get("composer")) or ""
        result["comment"] = _first(audio.tags.get("comment")) or ""
        lyrics = _first(audio.tags.get("lyrics"))
        if lyrics:
            result["_lyrics"] = str(lyrics)
            result["_lyrics_source"] = "ogg:LYRICS"
    except Exception as exc:
        print(f"    mutagen OGG: {exc}")
    return result


def read_tags(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".mp3":
        return _read_mp3(p)
    if ext == ".flac":
        return _read_flac(p)
    if ext in (".m4a", ".mp4", ".aac"):
        return _read_mp4(p)
    if ext in (".ogg", ".opus"):
        return _read_ogg(p)
    return {}


def save_cover(raw_tags: dict[str, Any], track_id: str, output_dir: Path) -> str:
    cover_data = raw_tags.get("_cover_data")
    if not cover_data:
        return ""
    mime = raw_tags.get("_cover_mime", "image/jpeg")
    ext = ".png" if "png" in mime.lower() else ".jpg"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{track_id}{ext}"
    out_path.write_bytes(cover_data)
    return str(out_path)


def extract_cover(path: str, track_id: str, output_dir: Path) -> str:
    """Совместимость со старым API."""
    return save_cover(read_tags(path), track_id, output_dir)


def read_sidecar_lyrics(path: str | Path) -> tuple[str, str]:
    """Ищет .lrc/.txt рядом с аудиофайлом."""
    audio_path = Path(path)
    for suffix, source in ((".lrc", "sidecar:LRC"), (".txt", "sidecar:TXT")):
        candidate = audio_path.with_suffix(suffix)
        if not candidate.exists():
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = candidate.read_text(encoding="cp1251", errors="ignore")
        if suffix == ".lrc":
            # Таймкоды нужны плееру, но мешают текстовому поиску.
            text = re.sub(r"\[\d{1,3}:\d{2}(?:[.:]\d+)?\]", "", text)
            text = re.sub(r"^\[[a-z]{2,10}:[^\]]*\]\s*$", "", text, flags=re.MULTILINE)
        if text.strip():
            return text.strip(), source
    return "", ""
