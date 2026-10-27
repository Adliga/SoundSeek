"""Проверка гибридного поиска на текущей базе."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_scripts._common import make_searcher
from soundseek_core.query_parser import parse_query

QUERIES = [
    "lonely day",
    "грустный рок",
    "весёлый панк",
    "рок, но не панк",
    "trap",
    "synthpop",
    "piano",
    "system of a down",
    "без вокала",
]


def main() -> None:
    searcher = make_searcher()
    for query in QUERIES:
        parsed = parse_query(query, searcher.ontology)
        print("\n" + "=" * 72)
        print(f"Запрос: {query}")
        print(f"Разбор: {parsed.describe()}")
        print("=" * 72)
        for index, hit in enumerate(searcher.search(query, top_k=5), 1):
            track = hit.track
            print(
                f"\n{index}. {track.display_title} — {track.tags.artist or '—'}"
            )
            print(
                f"   тип={track.derived.content_type or '—'}, "
                f"жанр={track.derived.genre or '—'}, "
                f"настроение={track.derived.mood or '—'}, "
                f"вокал={track.derived.has_vocal}"
            )
            print(f"   база={hit.base_score:.3f}, итог={hit.final_score:.3f}")
            for explanation in hit.explanations:
                print(f"   · {explanation}")


if __name__ == "__main__":
    main()
