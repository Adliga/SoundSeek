"""Поиск по текстам песен: лексический и мультиязычный семантический."""

from __future__ import annotations

from typing import Callable

from rapidfuzz import fuzz

from ..config import MIN_TEXT_SCORE
from ..db import VectorDB
from ..embeddings import TextEmbedder
from ..models import ParsedQuery, Track
from ..ontology import normalize_text, stem_word
from ..rules import tokenize

MIN_LYRICS_SEMANTIC = 0.82


def _token_matches(token: str, candidates: list[str]) -> bool:
    for candidate in candidates:
        if token == candidate or stem_word(token) == stem_word(candidate):
            return True
        if min(len(token), len(candidate)) >= 4 and fuzz.ratio(token, candidate) >= 88:
            return True
    return False


def lexical_score(track: Track, query: ParsedQuery) -> float:
    text = query.free_text
    tokens = tokenize(text)
    if not tokens or not track.derived.lyrics:
        return 0.0
    lyrics_norm = normalize_text(track.derived.lyrics)
    lyrics_tokens = tokenize(track.derived.lyrics)
    matched = sum(1 for token in tokens if _token_matches(token, lyrics_tokens))
    coverage = matched / len(tokens)
    phrase_bonus = 0.0
    for size in (min(3, len(tokens)), 2):
        if size < 2 or len(tokens) < size:
            continue
        for i in range(len(tokens) - size + 1):
            if " ".join(tokens[i : i + size]) in lyrics_norm:
                phrase_bonus = 0.35
                break
    if len(tokens) >= 2 and matched < 2 and phrase_bonus == 0.0:
        return 0.0
    return min(1.0, coverage + phrase_bonus)


def search_lyrics(
    db: VectorDB,
    query: ParsedQuery,
    text_embedder: Callable[[], TextEmbedder],
    top_k: int = 30,
) -> list[tuple[Track, float]]:
    text = query.free_text.strip()
    if not text:
        return []

    scores: dict[str, tuple[Track, float]] = {}
    for track in db.snapshot():
        score = lexical_score(track, query)
        if score >= MIN_TEXT_SCORE:
            scores[track.id] = (track, score)

    # Семантический канал имеет смысл только если в базе есть хотя бы один
    # ненулевой текстовый эмбеддинг.
    if db.has_text_embeddings():
        try:
            embedder = text_embedder()
            query_emb = embedder.encode(text, is_query=True)
            for track, similarity in db.search_text(query_emb, top_k=top_k):
                if similarity < MIN_LYRICS_SEMANTIC:
                    continue
                # E5 даёт высокий косинус даже для несвязанных текстов
                # (около 0.5–0.8), поэтому нужен отдельный порог.
                calibrated = max(
                    0.0,
                    min(1.0, (similarity - MIN_LYRICS_SEMANTIC) / 0.18),
                )
                if calibrated < MIN_TEXT_SCORE:
                    continue
                old = scores.get(track.id)
                if old is None:
                    scores[track.id] = (track, calibrated)
                else:
                    scores[track.id] = (
                        track,
                        max(old[1], 0.65 * old[1] + 0.35 * calibrated),
                    )
        except Exception as exc:
            print(f"  Лирический семантический канал недоступен: {exc}")

    results = [
        (track, round(score, 4))
        for track, score in scores.values()
        if score >= MIN_TEXT_SCORE
    ]
    results.sort(key=lambda item: (-item[1], item[0].display_title.lower()))
    return results[:top_k]
