from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FileTags:
    """Теги, извлечённые из самого аудиофайла."""
    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    year: Optional[int] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    genre: str = ""
    composer: str = ""
    comment: str = ""
    cover_path: str = ""


@dataclass
class DerivedData:
    """Данные, вычисленные системой."""
    content_type: str = ""
    genre: str = ""
    mood: str = ""
    has_vocal: bool = False
    lyrics: str = ""
    duration: float = 0.0
    user_notes: str = ""


@dataclass
class Track:
    id: str
    path: str
    tags: FileTags = field(default_factory=FileTags)
    derived: DerivedData = field(default_factory=DerivedData)