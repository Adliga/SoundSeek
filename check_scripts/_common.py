"""Общие пути для диагностических скриптов."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from soundseek_core.config import INDEX_PATH, TRACKS_DIR  # noqa: E402
from soundseek_core.indexer import AudioIndexer  # noqa: E402
from soundseek_core.ontology import Ontology  # noqa: E402
from soundseek_core.searcher import Searcher  # noqa: E402


def load_indexer(load_models: bool = True) -> AudioIndexer:
    return AudioIndexer(
        db_path=INDEX_PATH,
        ontology=Ontology(),
        load_models=load_models,
    )


def make_searcher(indexer: AudioIndexer | None = None) -> Searcher:
    indexer = indexer or load_indexer()
    return Searcher(indexer, indexer.ontology)


def first_audio() -> Path:
    files = sorted(
        path
        for path in TRACKS_DIR.rglob("*")
        if path.suffix.lower() in {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
    )
    if not files:
        raise SystemExit("В data/tracks/ нет аудиофайлов.")
    return files[0]
