"""Поиск по мелодическому контуру (query-by-humming)."""

from __future__ import annotations

from ..melody import (
    chroma_similarity,
    extract_chroma,
    extract_melody,
    melody_similarity,
)
from ..models import Track

MIN_MELODY_SCORE = 0.38


def search_melody(
    tracks: list[Track],
    query_audio,
    top_k: int = 30,
) -> list[tuple[Track, float]]:
    query = extract_melody(query_audio)
    query_chroma = extract_chroma(query_audio)
    if query.size == 0 and query_chroma.size == 0:
        return []
    scored: list[tuple[Track, float]] = []
    for track in tracks:
        contour = track.derived.melody_contour
        chroma = track.derived.melody_chroma
        contour_score = (
            melody_similarity(query, contour) if len(contour) else 0.0
        )
        chroma_score = (
            chroma_similarity(query_chroma, chroma)
            if len(chroma) and query_chroma.size
            else 0.0
        )
        if contour_score and chroma_score:
            score = 0.5 * contour_score + 0.5 * chroma_score
        else:
            score = max(contour_score, chroma_score)
        if score >= MIN_MELODY_SCORE:
            scored.append((track, score))
    scored.sort(key=lambda item: (-item[1], item[0].display_title.lower()))
    return scored[:top_k]
