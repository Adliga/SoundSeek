"""Генерация плейлиста по настроению и жанру.

Простой жадный алгоритм: для каждой позиции выбирается трек, ближайший к
целевой точке (valence, arousal), с бонусом за жанр и штрафом за повтор
исполнителя. Это объяснимо и не требует обучения.
"""

from __future__ import annotations

from dataclasses import dataclass

from .db import VectorDB
from .models import Track
from .ontology import Ontology

MOOD_SPACE: dict[str, tuple[float, float]] = {
    "happy": (0.90, 0.65),
    "energetic": (0.80, 0.90),
    "uplifting": (0.85, 0.65),
    "cheerful": (0.90, 0.60),
    "euphoric": (0.95, 0.90),
    "sad": (0.10, 0.25),
    "melancholic": (0.20, 0.25),
    "lonely": (0.15, 0.20),
    "nostalgic": (0.45, 0.30),
    "heartbroken": (0.05, 0.35),
    "gloomy": (0.10, 0.20),
    "aggressive": (0.25, 0.90),
    "angry": (0.10, 0.95),
    "intense": (0.40, 0.90),
    "dark": (0.15, 0.40),
    "rebellious": (0.30, 0.85),
    "calm": (0.65, 0.15),
    "peaceful": (0.70, 0.10),
    "dreamy": (0.60, 0.20),
    "relaxing": (0.75, 0.15),
    "meditative": (0.65, 0.10),
    "romantic": (0.70, 0.30),
    "sensual": (0.60, 0.35),
    "epic": (0.70, 0.85),
    "cinematic": (0.55, 0.50),
    "playful": (0.80, 0.70),
    "quirky": (0.60, 0.60),
    "mysterious": (0.40, 0.35),
    "ominous": (0.10, 0.50),
}


@dataclass
class PlaylistItem:
    track: Track
    score: float
    reason: str


def _point(mood: str) -> tuple[float, float]:
    return MOOD_SPACE.get(mood, (0.5, 0.5))


def _distance(
    left: tuple[float, float], right: tuple[float, float]
) -> float:
    return ((left[0] - right[0]) ** 2 + (left[1] - right[1]) ** 2) ** 0.5


def generate_playlist(
    db: VectorDB,
    ontology: Ontology,
    target_mood: str = "",
    start_mood: str = "",
    end_mood: str = "",
    length: int = 10,
    genre: str = "",
) -> list[PlaylistItem]:
    tracks = [
        track
        for track in db.snapshot()
        if track.derived.content_type in ("", "music", "singing")
    ]
    if not tracks:
        return []

    if start_mood and end_mood:
        start = _point(start_mood)
        end = _point(end_mood)
        trajectory = [
            (
                start[0] + (end[0] - start[0]) * i / max(1, length - 1),
                start[1] + (end[1] - start[1]) * i / max(1, length - 1),
            )
            for i in range(length)
        ]
    else:
        point = _point(target_mood)
        trajectory = [point] * length

    selected: list[PlaylistItem] = []
    used_ids: set[str] = set()
    used_artists: dict[str, int] = {}
    selected_genres: dict[str, int] = {}

    for slot, target in enumerate(trajectory):
        best: tuple[float, Track, str] | None = None
        for track in tracks:
            if track.id in used_ids:
                continue
            track_point = _point(track.derived.mood)
            distance = _distance(target, track_point)
            score = 1.0 - distance / 1.414
            reason = f"настроение {track.derived.mood or 'не определено'}"
            if genre and track.derived.genre:
                relation = ontology.genre_distance(genre, track.derived.genre)
                if relation is not None and relation <= 2:
                    bonus = 0.20 if relation == 0 else 0.10
                    score += bonus
                    reason += f"; жанр {track.derived.genre}"
            artist = (track.tags.artist or "—").lower()
            if used_artists.get(artist):
                score -= 0.18 * used_artists[artist]
                reason += "; разнообразие исполнителей"
            if selected_genres.get(track.derived.genre):
                score -= 0.03 * selected_genres[track.derived.genre]
            if track.derived.has_vocal is None:
                score -= 0.02
            if best is None or score > best[0]:
                best = (score, track, reason)

        if best is None:
            break
        score, track, reason = best
        selected.append(PlaylistItem(track, round(score, 4), reason))
        used_ids.add(track.id)
        artist = (track.tags.artist or "—").lower()
        used_artists[artist] = used_artists.get(artist, 0) + 1
        selected_genres[track.derived.genre] = (
            selected_genres.get(track.derived.genre, 0) + 1
        )
    return selected
