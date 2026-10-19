from pathlib import Path
from typing import Optional, Dict, Any

from mutagen import File as MutagenFile
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4


COVERS_DIR_NAME = "covers"


def _extract_year(value) -> Optional[int]:
    """Пытается вытащить год из строки вида '2005', '2005-04-12' и т. п."""
    if not value:
        return None
    if isinstance(value, int):
        return value
    text = str(value)
    for token in text.replace("-", " ").replace("/", " ").split():
        if token.isdigit() and len(token) == 4:
            return int(token)
    return None


def _first(value):
    """Возвращает первый элемент, если пришёл список, иначе само значение."""
    if isinstance(value, list) and value:
        return value[0]
    return value


def _read_mp3(path: Path) -> Dict[str, Any]:
    result = {}
    try:
        audio = MP3(str(path), ID3=ID3)
        if audio.tags is None:
            return result

        tags = audio.tags
        result["title"] = str(tags.get("TIT2", ""))
        result["artist"] = str(tags.get("TPE1", ""))
        result["album"] = str(tags.get("TALB", ""))
        result["year"] = _extract_year(tags.get("TDRC") or tags.get("TYER"))
        result["genre"] = str(tags.get("TCON", ""))

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
        result["title"] = _first(audio.get("title"))
        result["artist"] = _first(audio.get("artist"))
        result["album"] = _first(audio.get("album"))
        result["year"] = _extract_year(_first(audio.get("date")))
        result["genre"] = _first(audio.get("genre"))
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
        result["title"] = _first(audio.get("\xa9nam"))
        result["artist"] = _first(audio.get("\xa9ART"))
        result["album"] = _first(audio.get("\xa9alb"))
        result["year"] = _extract_year(_first(audio.get("\xa9day")))
        result["genre"] = _first(audio.get("\xa9gen"))
        covers = audio.get("covr")
        if covers:
            result["_cover_data"] = bytes(covers[0])
            result["_cover_mime"] = "image/jpeg"
    except Exception as e:
        print(f"    mutagen MP4: {e}")
    return result


def _read_ogg(path: Path) -> Dict[str, Any]:
    """OGG/OPUS через общий MutagenFile."""
    result = {}
    try:
        audio = MutagenFile(str(path))
        if audio is None or audio.tags is None:
            return result
        result["title"] = _first(audio.tags.get("title"))
        result["artist"] = _first(audio.tags.get("artist"))
        result["album"] = _first(audio.tags.get("album"))
        result["year"] = _extract_year(_first(audio.tags.get("date")))
        result["genre"] = _first(audio.tags.get("genre"))
    except Exception as e:
        print(f"    mutagen OGG: {e}")
    return result


def read_tags(path: str) -> Dict[str, Any]:
    """Читает теги из аудиофайла. Возвращает словарь с полями:

    title, artist, album, year, genre, _cover_data, _cover_mime
    """
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
    """Извлекает обложку из аудиофайла и сохраняет её в output_dir.

    Возвращает путь к сохранённому изображению или пустую строку,
    если обложки нет.
    """
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