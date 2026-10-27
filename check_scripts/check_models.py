"""Проверка загрузки моделей на CPU."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from soundseek_core.embeddings import AudioEmbedder, TextEmbedder


def main() -> None:
    start = time.time()
    audio = AudioEmbedder()
    print(f"CLAP загружен за {time.time() - start:.1f} с")
    start = time.time()
    vector = audio.embed_text("calm piano music")
    print(f"CLAP text: {vector.shape} за {time.time() - start:.2f} с")

    start = time.time()
    text = TextEmbedder()
    print(f"Текстовая модель {text.model_name} за {time.time() - start:.1f} с")
    start = time.time()
    vector = text.encode("спокойная музыка", is_query=True)
    print(f"Текст: {vector.shape} за {time.time() - start:.3f} с")


if __name__ == "__main__":
    main()
