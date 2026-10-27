"""Лексический поиск по метаданным.

Канал намеренно не смотрит на полный путь: иначе слово ``music`` в
``.../Music Video/`` повышает все треки. Поля взвешиваются, а совпадение
фразы ценится выше совпадения отдельных слов.
"""

from __future__ import annotations

from typing import Iterable

from rapidfuzz import fuzz

from ..config import MIN_METADATA_SCORE
from ..models import ParsedQuery, Track
from ..ontology import normalize_text, stem_word
from ..rules import tokenize

FIELD_WEIGHTS = {
    "title": 1.0,
    "artist": 0.95,
    "album": 0.65,
    "album_artist": 0.85,
    "stem": 0.85,
    "comment": 0.35,
    "composer": 0.45,
}


def _field_tokens(value: str) -> list[str]:
    return tokenize(value)


def _token_matches(token: str, candidates: Iterable[str]) -> bool:
    for candidate in candidates:
        if token == candidate or stem_word(token) == stem_word(candidate):
            return True
        if min(len(token), len(candidate)) >= 4 and fuzz.ratio(token, candidate) >= 88:
            return True
    return False


def _field_score(query_tokens: list[str], value: str) -> float:
    if not query_tokens or not value:
        return 0.0
    tokens = _field_tokens(value)
    if not tokens:
        return 0.0
    matched = sum(1 for token in query_tokens if _token_matches(token, tokens))
    coverage = matched / len(query_tokens)
    normalized = normalize_text(value)
    phrase_bonus = 0.0
    for size in (min(3, len(query_tokens)), 2):
        if size < 2 or len(query_tokens) < size:
            continue
        for i in range(len(query_tokens) - size + 1):
            if " ".join(query_tokens[i : i + size]) in normalized:
                phrase_bonus = 0.25
                break
    # Для запроса из нескольких слов одного случайного совпадения мало:
    # «system of a down» не должен повышать трек только за слово down.
    if len(query_tokens) >= 2 and matched < 2 and phrase_bonus == 0.0:
        return 0.0
    return min(1.0, coverage + phrase_bonus)


def score_track(track: Track, query: ParsedQuery) -> float:
    text = query.artist or query.free_text
    tokens = tokenize(text)
    if not tokens:
        return 0.0
    fields = {
        "title": track.tags.title,
        "artist": track.tags.artist,
        "album": track.tags.album,
        "album_artist": track.tags.album_artist,
        "stem": track.stem,
        "comment": track.tags.comment,
        "composer": track.tags.composer,
    }
    total_weight = sum(FIELD_WEIGHTS.values())
    score = 0.0
    for field, value in fields.items():
        score += FIELD_WEIGHTS[field] * _field_score(tokens, value)
    score /= total_weight
    # Если весь запрос целиком встречается в заголовке/исполнителе/файле,
    # это сильнее любого частичного совпадения.
    exact_text = normalize_text(text)
    for field in ("title", "artist", "stem"):
        value = normalize_text(fields[field])
        if value and exact_text and exact_text in value:
            score = max(score, 1.0)
            break
    return round(score, 4)


def search_metadata(
    tracks: list[Track], query: ParsedQuery, top_k: int = 50
) -> list[tuple[Track, float]]:
    scored = [
        (track, score_track(track, query))
        for track in tracks
    ]
    scored = [
        (track, score)
        for track, score in scored
        if score >= MIN_METADATA_SCORE
    ]
    scored.sort(key=lambda item: (-item[1], item[0].display_title.lower()))
    return scored[:top_k]
