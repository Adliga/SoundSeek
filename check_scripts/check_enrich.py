"""Запуск тяжёлого обогащения для необработанных музыкальных треков."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_scripts._common import load_indexer


def main() -> None:
    indexer = load_indexer()
    total = indexer.enrich_with_lyrics()
    print(f"Обработано треков: {total}")


if __name__ == "__main__":
    main()
