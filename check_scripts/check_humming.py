import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["DEMUCS_DEVICE"] = "cpu"

import numpy as np
import librosa
import soundfile as sf

from soundseek_core import AudioIndexer
from soundseek_core.ontology import Ontology
from soundseek_core.searcher import Searcher


TEST_TRACK = "data/New Light - Dalby.mp3"
TEST_FRAGMENT = "data/test_hum.wav"


def prepare_fragment(source: str, output: str, seconds: float = 8.0):
    """Берёт фрагмент из середины трека и сохраняет как wav — имитация напевания."""
    if Path(output).exists():
        print(f"Фрагмент уже существует: {output}")
        return

    duration = librosa.get_duration(path=source)
    start = (duration - seconds) / 2
    audio, _ = librosa.load(source, sr=48000, offset=start, duration=seconds, mono=True)
    sf.write(output, audio, 48000)
    print(f"Создан фрагмент: {output} ({seconds} сек)")


def main():
    # Готовим тестовый фрагмент
    prepare_fragment(TEST_TRACK, TEST_FRAGMENT, seconds=8.0)

    # Загружаем систему
    indexer = AudioIndexer(db_path="data/library")
    ontology = Ontology()
    searcher = Searcher(indexer, ontology)

    # Поиск по аудио
    print("\n" + "=" * 70)
    print(f"Поиск по фрагменту: {TEST_FRAGMENT}")
    print("=" * 70)

    results = searcher.search_by_audio(TEST_FRAGMENT, top_k=3)

    for i, r in enumerate(results, 1):
        t = r["track"]
        print(f"\n{i}. {t.id}")
        print(f"   genre: {t.genre}, mood: {t.mood}")
        print(f"   base_score:  {r['base_score']}")
        print(f"   final_score: {r['final_score']}")
        print(f"   Объяснение:")
        for line in r["explanations"]:
            print(f"     • {line}")


if __name__ == "__main__":
    main()