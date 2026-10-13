from dataclasses import dataclass
from typing import Optional


@dataclass
class Track:
    id: str
    path: str
    title: str = ""
    artist: str = ""
    album: str = ""
    year: Optional[int] = None
    genre: str = ""
    mood: str = ""
    duration: float = 0.0
    has_vocal: bool = False
    lyrics: str = ""