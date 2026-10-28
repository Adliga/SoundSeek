"""Поиск по личным заметкам пользователя.

Заметки — короткие авторские пометки вроде «для тренировки» или «на
повтор». Они не являются текстом песни и не должны смешиваться с
лирическим каналом, поэтому для них выделен отдельный лексический канал.
Канал работает по всей библиотеке, а не только по кандидатам CLAP.
"""

from __future__ import annotations

from rapidfuzz import fuzz

from ..models import ParsedQuery, Track
from ..ontology import normalize_text, stem_word
from ..rules import tokenize

MIN_NOTES_SCORE = 0.30


def _token_matches(token: str, candidates: list[str]) -> bool:
    for candidate in candidates:
        if token == candidate or stem_word(token) == stem_word(candidate):
            return True
        if min(len(token), len(candidate)) >= 4 and fuzz.ratio(token, candidate) >= 88:
            return True
    return False


def score_track(track: Track, query: ParsedQuery) -> float:
    """Оценивает заметку по покрытию слов запроса.

    Для заметок не требуется двух совпадений, как для длинных метаданных:
    одна осмысленная пометка уже является сильным сигналом.
    """
    notes = (track.derived.user_notes or "").strip()
    if not notes:
        return 0.0
    text = (query.free_text or query.raw or "").strip()
    tokens = tokenize(text)
    if not tokens:
        return 0.0

    notes_norm = normalize_text(notes)
    notes_tokens = tokenize(notes)
    if not notes_tokens:
        return 0.0

    matched = [token for token in tokens if _token_matches(token, notes_tokens)]
    if not matched:
        return 0.0

    coverage = len(matched) / len(tokens)
    # Фраза из двух-трёх слов — самый надёжный вариант.
    for size in (min(3, len(tokens)), 2):
        if size < 2 or len(tokens) < size:
            continue
        for index in range(len(tokens) - size + 1):
            phrase = " ".join(tokens[index : index + size])
            if phrase in notes_norm:
                return 1.0
    return min(1.0, 0.5 + 0.5 * coverage)


def search_notes(
    tracks: list[Track],
    query: ParsedQuery,
    top_k: int = 30,
) -> list[tuple[Track, float]]:
    scored = [
        (track, score_track(track, query))
        for track in tracks
    ]
    scored = [
        (track, score)
        for track, score in scored
        if score >= MIN_NOTES_SCORE
    ]
    scored.sort(key=lambda item: (-item[1], item[0].display_title.lower()))
    return scored[:top_k]
