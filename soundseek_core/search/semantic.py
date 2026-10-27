"""Семантические каналы: CLAP по текстовому описанию и по аудио."""

from __future__ import annotations

from ..config import MIN_CLAP_SCORE
from ..db import VectorDB
from ..indexer import AudioIndexer
from ..models import ParsedQuery


def search_text(
    db: VectorDB,
    indexer: AudioIndexer,
    query: ParsedQuery,
    top_k: int = 30,
) -> list[tuple]:
    text = query.semantic_text or query.free_text or query.raw
    if not text.strip():
        return []
    try:
        embedding = indexer.get_query_text_embedding(text)
        results = db.search_audio(embedding, top_k=top_k)
    except Exception as exc:
        print(f"  CLAP-канал недоступен: {exc}")
        return []
    return [(track, score) for track, score in results if score >= MIN_CLAP_SCORE]


def search_audio(
    db: VectorDB,
    indexer: AudioIndexer,
    audio,
    top_k: int = 30,
) -> list[tuple]:
    try:
        embedding = indexer.get_audio_embedding(audio, segments=1)
        results = db.search_audio(embedding, top_k=top_k)
    except Exception as exc:
        print(f"  Аудиоканал недоступен: {exc}")
        return []
    return [(track, score) for track, score in results if score >= 0.10]
