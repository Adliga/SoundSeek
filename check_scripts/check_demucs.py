"""Проверка Demucs на первом файле библиотеки."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_scripts._common import first_audio
from soundseek_core.enrichment import EnrichmentService


def main() -> None:
    source = first_audio()
    with tempfile.TemporaryDirectory() as tmp:
        print(f"Источник: {source.name}")
        start = time.time()
        vocals = EnrichmentService._separate_vocals(str(source), tmp)
        print(f"Время: {time.time() - start:.1f} с")
        print(f"Вокал: {vocals}")


if __name__ == "__main__":
    main()
