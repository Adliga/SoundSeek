"""Модель данных SoundSeek.

Dataclass'ы намеренно имеют значения по умолчанию и ``__setstate__``:
это позволяет загружать старые pickle-индексы без ручной миграции.
"""

from __future__ import annotations

from dataclasses import MISSING, dataclass, field, fields
from pathlib import Path
from typing import Any, Optional


def _restore_defaults(obj: Any) -> None:
    """Заполняет поля, которых не было в старом pickle-индексе."""
    for f in fields(obj):
        if hasattr(obj, f.name):
            continue
        if f.default is not MISSING:
            setattr(obj, f.name, f.default)
        elif f.default_factory is not MISSING:  # type: ignore[misc]
            setattr(obj, f.name, f.default_factory())


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

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
        _restore_defaults(self)


@dataclass
class LyricsSegment:
    start: float = 0.0
    end: float = 0.0
    text: str = ""


@dataclass
class DerivedData:
    """Данные, вычисленные системой."""

    content_type: str = ""
    content_type_confidence: float = 0.0
    genre: str = ""
    genre_source: str = ""
    genre_confidence: float = 0.0
    mood: str = ""
    mood_confidence: float = 0.0
    has_vocal: Optional[bool] = None
    lyrics: str = ""
    lyrics_source: str = ""
    lyrics_language: str = ""
    lyrics_segments: list[LyricsSegment] = field(default_factory=list)
    melody_contour: list[float] = field(default_factory=list)
    melody_chroma: list[list[float]] = field(default_factory=list)
    duration: float = 0.0
    user_notes: str = ""
    enrich_status: str = "idle"
    enrich_error: str = ""
    enrich_attempted_at: Optional[float] = None
    confidences: dict[str, Any] = field(default_factory=dict)

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
        _restore_defaults(self)
        # Старые индексы хранили has_vocal как bool. Если вокал не найден и
        # трек ещё не обогащался, правильное состояние — «неизвестно».
        if (
            self.has_vocal is False
            and not self.lyrics
            and not self.enrich_attempted_at
            and self.enrich_status in ("", "idle")
        ):
            self.has_vocal = None
        if isinstance(self.lyrics_segments, list):
            self.lyrics_segments = [
                seg if isinstance(seg, LyricsSegment) else LyricsSegment(**seg)
                for seg in self.lyrics_segments
                if isinstance(seg, (LyricsSegment, dict))
            ]
        if not isinstance(self.confidences, dict):
            self.confidences = {}


@dataclass
class Track:
    id: str
    path: str
    tags: FileTags = field(default_factory=FileTags)
    derived: DerivedData = field(default_factory=DerivedData)
    relative_path: str = ""
    file_size: int = 0
    file_mtime: float = 0.0
    index_version: int = 0
    manual_fields: list[str] = field(default_factory=list)

    @property
    def stem(self) -> str:
        return Path(self.path).stem

    @property
    def display_title(self) -> str:
        if self.tags.title:
            return self.tags.title
        # Имена файлов часто используют подчёркивания вместо пробелов.
        return self.stem.replace("_", " ").strip() or self.stem

    @property
    def effective_genre(self) -> str:
        return self.derived.genre or ""

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
        _restore_defaults(self)
        if isinstance(self.tags, dict):
            self.tags = FileTags(**self.tags)
        if isinstance(self.derived, dict):
            self.derived = DerivedData(**self.derived)
        if not self.relative_path:
            self.relative_path = Path(self.path).name
        if not isinstance(self.manual_fields, list):
            self.manual_fields = list(self.manual_fields or [])


@dataclass
class ParsedQuery:
    """Результат разбора пользовательского запроса."""

    raw: str = ""
    genres: list[str] = field(default_factory=list)
    moods: list[str] = field(default_factory=list)
    negated_genres: list[str] = field(default_factory=list)
    negated_moods: list[str] = field(default_factory=list)
    has_vocal: Optional[bool] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    artist: str = ""
    free_text: str = ""
    semantic_text: str = ""

    def describe(self) -> str:
        parts: list[str] = []
        if self.genres:
            parts.append("жанр: " + ", ".join(self.genres))
        if self.moods:
            parts.append("настроение: " + ", ".join(self.moods))
        if self.negated_genres:
            parts.append("исключить жанры: " + ", ".join(self.negated_genres))
        if self.negated_moods:
            parts.append("исключить настроения: " + ", ".join(self.negated_moods))
        if self.has_vocal is True:
            parts.append("только с вокалом")
        elif self.has_vocal is False:
            parts.append("без вокала")
        if self.year_from or self.year_to:
            parts.append(f"годы: {self.year_from or '…'}–{self.year_to or '…'}")
        if self.artist:
            parts.append(f"исполнитель: {self.artist}")
        if self.free_text:
            parts.append(f"текст запроса: {self.free_text}")
        return "; ".join(parts) if parts else "явных сущностей не найдено"


@dataclass
class SearchHit:
    """Один результат поиска с прозрачным разбором оценки."""

    track: Track
    base_score: float
    final_score: float
    explanations: list[str] = field(default_factory=list)
    rule_hits: list[Any] = field(default_factory=list)
    channels: dict[str, float] = field(default_factory=dict)
    channel_ranks: dict[str, int] = field(default_factory=dict)
    rank: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "track": self.track,
            "base_score": self.base_score,
            "final_score": self.final_score,
            "explanations": self.explanations,
            "rule_hits": self.rule_hits,
            "channels": self.channels,
            "channel_ranks": self.channel_ranks,
            "rank": self.rank,
        }

    # Совместимость со старым кодом, который обращался к результату как к dict.
    def __getitem__(self, key: str) -> Any:
        return self.as_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.as_dict().get(key, default)
