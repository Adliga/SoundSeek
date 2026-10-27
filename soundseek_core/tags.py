from pathlib import Path
from typing import Optional, Dict, Any

from mutagen import File as MutagenFile
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
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


def _read_mp3(path: Path) -> Dict[str, Any]:
    result = {}
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
    except Exception as e:
        print(f"    mutagen MP3: {e}")
    return result


def _read_flac(path: Path) -> Dict[str, Any]:
    result = {}
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
        if audio.pictures:
            pic = audio.pictures[0]
            result["_cover_data"] = pic.data
            result["_cover_mime"] = pic.mime
    except Exception as e:
        print(f"    mutagen FLAC: {e}")
    return result


def _read_mp4(path: Path) -> Dict[str, Any]:
    result = {}
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
        covers = audio.get("covr")
        if covers:
            result["_cover_data"] = bytes(covers[0])
            result["_cover_mime"] = "image/jpeg"
    except Exception as e:
        print(f"    mutagen MP4: {e}")
    return result


def _read_ogg(path: Path) -> Dict[str, Any]:
    result = {}
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
    except Exception as e:
        print(f"    mutagen OGG: {e}")
    return result


def read_tags(path: str) -> Dict[str, Any]:
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


def extract_cover(path: str, track_id: str, output_dir: Path) -> str:
    tags = read_tags(path)
    cover_data = tags.get("_cover_data")
    if not cover_data:
        return ""

    mime = tags.get("_cover_mime", "image/jpeg")
    ext = ".png" if "png" in mime.lower() else ".jpg"

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{track_id}{ext}"
    out_path.write_bytes(cover_data)
    return str(out_path)