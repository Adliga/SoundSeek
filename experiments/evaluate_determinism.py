"""Проверка воспроизводимости CLAP-эмбеддинга и классификации."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from soundseek_core.audio import load_middle
from soundseek_core.classifier import AudioClassifier
from soundseek_core.config import INDEX_PATH
from soundseek_core.embeddings import AudioEmbedder
from soundseek_core.indexer import AudioIndexer
from soundseek_core.ontology import Ontology


def main() -> None:
    tracks = AudioIndexer(db_path=INDEX_PATH, load_models=False).db.snapshot()
    music = [track for track in tracks if track.derived.content_type == "music"]
    if not music:
        raise SystemExit("В библиотеке нет музыкальных треков.")
    track = music[0]
    audio = load_middle(track.path)
    embedder = AudioEmbedder()
    classifier = AudioClassifier(embedder, Ontology())

    embeddings = [embedder.embed_audio(audio, segments=3) for _ in range(3)]
    cosines = [
        float(np.dot(embeddings[0], other)) for other in embeddings
    ]
    labels = [
        classifier.classify(
            embeddings[0],
            duration=track.derived.duration,
            tag_genre=track.tags.genre,
            filename=Path(track.path).name,
        )
        for _ in range(3)
    ]
    result = {
        "track": track.display_title,
        "cosine_repeats": [round(value, 6) for value in cosines],
        "labels": [
            {
                "content_type": item.content_type,
                "genre": item.genre,
                "genre_source": item.genre_source,
                "mood": item.mood,
                "has_vocal": item.has_vocal,
            }
            for item in labels
        ],
        "deterministic": all(value > 0.9999 for value in cosines)
        and len({(item.content_type, item.genre, item.mood) for item in labels})
        == 1,
    }
    output = Path("experiments/results/determinism.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
