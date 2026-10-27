"""Диагностика каналов: метаданные, CLAP, текст, аудио."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_scripts._common import make_searcher


def main() -> None:
    searcher = make_searcher()
    indexer = searcher.indexer
    db = indexer.db

    print(f"Треков: {len(db)}; текстовых эмбеддингов: {db.has_text_embeddings()}")
    for index, track in enumerate(db.snapshot(), 1):
        print(
            f"{index:2}. {track.display_title[:55]:55} | "
            f"{track.derived.content_type:8} | "
            f"{track.derived.genre or '—':16} | "
            f"{track.derived.mood or '—':12} | "
            f"вокал={track.derived.has_vocal} | "
            f"текст={len(track.derived.lyrics)}"
        )

    print("\n--- CLAP: текстовые запросы ---")
    for query in ["piano", "heavy metal", "calm ambient", "rap"]:
        embedding = indexer.get_query_text_embedding(query)
        print(f"\n{query}:")
        for track, score in db.search_audio(embedding, top_k=3):
            print(f"  {score:.3f}  {track.display_title}")

    print("\n--- Текстовый канал ---")
    for query in ["lonely day", "родина", "война"]:
        embedding = indexer.text_embedder.encode(query, is_query=True)
        print(f"\n{query}:")
        for track, score in db.search_text(embedding, top_k=3):
            print(f"  {score:.3f}  {track.display_title}")


if __name__ == "__main__":
    main()
