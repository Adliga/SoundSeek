"""Оценка качества поиска и ablation-анализ каналов.

Метрики считаются на небольшом ручном наборе запросов к текущей
аудиотеке. Это не замена полноценному бенчмарку, но позволяет
контролировать регрессии и сравнивать вклад каналов.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from soundseek_core.config import INDEX_PATH
from soundseek_core.indexer import AudioIndexer
from soundseek_core.models import ParsedQuery, Track
from soundseek_core.query_parser import parse_query
from soundseek_core.rules import RuleEngine
from soundseek_core.search import fusion, lyrics, metadata, notes, semantic


@dataclass
class Case:
    query: str
    expected: Callable[[Track], bool]
    description: str


def _haystack(track: Track) -> str:
    return f"{track.display_title} {track.tags.artist or ''} {track.relative_path}".lower()


CASES = [
    Case(
        "lonely day",
        lambda t: "lonely" in _haystack(t),
        "точное название",
    ),
    Case(
        "cigaro",
        lambda t: "cigaro" in _haystack(t),
        "точное название",
    ),
    Case(
        "new light",
        lambda t: "new light" in _haystack(t),
        "точное название",
    ),
    Case(
        "maanam",
        lambda t: "maanam" in _haystack(t),
        "исполнитель",
    ),
    Case(
        "король и шут",
        lambda t: "король и шут" in _haystack(t),
        "исполнитель, кириллица",
    ),
    Case(
        "piano",
        lambda t: "new light" in _haystack(t),
        "описание звучания",
    ),
    Case(
        "весёлый панк",
        lambda t: t.derived.genre == "punk_rock",
        "жанр + настроение",
    ),
    Case(
        "рок, но не панк",
        lambda t: t.derived.genre
        and t.derived.genre != "punk_rock"
        and "punk" not in t.derived.genre,
        "отрицание",
    ),
    Case(
        "trap",
        lambda t: t.derived.genre in ("trap", "rap"),
        "близкий поджанр",
    ),
    Case(
        "2010-е",
        lambda t: t.tags.year is not None and 2010 <= t.tags.year <= 2019,
        "десятилетие",
    ),
    Case(
        "с вокалом",
        lambda t: t.derived.has_vocal is True,
        "фильтр вокала",
    ),
]


def _resolve_expected(tracks: list[Track], case: Case) -> set[str]:
    return {track.id for track in tracks if case.expected(track)}


def _metrics(
    ranks: list[int],
    expected_count: int,
    k: int,
) -> dict[str, float]:
    hits = [rank for rank in ranks if rank <= k]
    precision = len(hits) / k if k else 0.0
    recall = len(hits) / expected_count if expected_count else 0.0
    mrr = 1.0 / min(ranks) if ranks else 0.0
    return {
        f"precision@{k}": round(precision, 4),
        f"recall@{k}": round(recall, 4),
        "mrr": round(mrr, 4),
    }


def _ablation_hits(
    indexer: AudioIndexer,
    parsed: ParsedQuery,
    mode: str,
    top_k: int,
) -> list:
    tracks = indexer.db.snapshot()
    channels: dict[str, list[tuple]] = {}
    if mode in ("full", "metadata"):
        result = metadata.search_metadata(tracks, parsed, top_k=40)
        if result:
            channels["metadata"] = result
    if mode in ("full", "clap"):
        result = semantic.search_text(indexer.db, indexer, parsed, top_k=40)
        if result:
            channels["clap"] = result
    if mode in ("full", "lyrics"):
        result = lyrics.search_lyrics(
            indexer.db, parsed, lambda: indexer.text_embedder, top_k=30
        )
        if result:
            channels["lyrics"] = result
    if mode == "full":
        result = notes.search_notes(tracks, parsed, top_k=40)
        if result:
            channels["notes"] = result
    if mode == "full" and (
        parsed.year_from is not None
        or parsed.year_to is not None
        or parsed.has_vocal is not None
        or parsed.negated_genres
        or parsed.negated_moods
    ):
        channels["filter"] = [(track, 1.0) for track in tracks]
    if not channels:
        return []
    engine = RuleEngine(indexer.ontology)
    hits = engine.apply(parsed, fusion.fuse(channels))
    if mode == "full" and len(hits) > 1 and hits[0].final_score >= 0.45:
        cutoff = max(0.10, hits[0].final_score * 0.45)
        hits = [hit for hit in hits if hit.final_score >= cutoff]
    return hits[:top_k]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", default="experiments/results/search_metrics.json"
    )
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    indexer = AudioIndexer(db_path=INDEX_PATH, load_models=True)
    tracks = indexer.db.snapshot()
    modes = ["metadata", "clap", "lyrics", "full"]
    report = {"cases": [], "summary": {}}

    for mode in modes:
        rows = []
        total_precision = 0.0
        total_recall = 0.0
        total_mrr = 0.0
        for case in CASES:
            expected = _resolve_expected(tracks, case)
            parsed = parse_query(case.query, indexer.ontology)
            hits = _ablation_hits(indexer, parsed, mode, args.top_k)
            ranks = [
                index + 1
                for index, hit in enumerate(hits)
                if hit.track.id in expected
            ]
            metrics = _metrics(ranks, max(1, len(expected)), args.top_k)
            total_precision += metrics[f"precision@{args.top_k}"]
            total_recall += metrics[f"recall@{args.top_k}"]
            total_mrr += metrics["mrr"]
            rows.append(
                {
                    "query": case.query,
                    "description": case.description,
                    "expected": sorted(expected),
                    "returned": [hit.track.display_title for hit in hits],
                    "ranks": ranks,
                    **metrics,
                }
            )
        count = len(CASES)
        report["summary"][mode] = {
            f"mean_precision@{args.top_k}": round(total_precision / count, 4),
            f"mean_recall@{args.top_k}": round(total_recall / count, 4),
            "mean_mrr": round(total_mrr / count, 4),
        }
        report["cases"].append({"mode": mode, "cases": rows})

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Сохранено: {output}")


if __name__ == "__main__":
    main()
