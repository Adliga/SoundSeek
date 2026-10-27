"""Просмотр распознанных и встроенных текстов."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_scripts._common import load_indexer


def main() -> None:
    indexer = load_indexer(load_models=False)
    for track in indexer.db.snapshot():
        if not track.derived.lyrics:
            continue
        print("\n" + "=" * 72)
        print(f"{track.display_title} — {track.tags.artist or '—'}")
        print(
            f"источник={track.derived.lyrics_source or '—'}, "
            f"язык={track.derived.lyrics_language or '—'}, "
            f"статус={track.derived.enrich_status}"
        )
        print(track.derived.lyrics[:800])


if __name__ == "__main__":
    main()
