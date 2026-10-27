"""Полный диагностический прогон: синхронизация и поиск."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_scripts._common import make_searcher


def main() -> None:
    searcher = make_searcher()
    stats = searcher.indexer.sync_folder()
    print(stats.summary())

    for query in ["calm piano music", "energetic rock", "sad slow melody"]:
        print(f"\n{query}:")
        for hit in searcher.search(query, top_k=3):
            print(f"  {hit.final_score:.3f}  {hit.track.display_title}")


if __name__ == "__main__":
    main()
