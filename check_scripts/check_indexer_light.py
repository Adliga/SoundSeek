"""Инкрементальная индексация data/tracks."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_scripts._common import TRACKS_DIR, load_indexer


def main() -> None:
    indexer = load_indexer()
    stats = indexer.sync_folder(TRACKS_DIR)
    print(stats.summary())


if __name__ == "__main__":
    main()
