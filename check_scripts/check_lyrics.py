import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["DEMUCS_DEVICE"] = "cpu"

from soundseek_core import AudioIndexer


def main():
    indexer = AudioIndexer(db_path="data/library")

    for track in indexer.db.tracks:
        print(f"\n{'='*70}")
        print(f"ID: {track.id}")
        print(f"genre: {track.genre}, mood: {track.mood}")
        print(f"has_vocal: {track.has_vocal}")
        print(f"lyrics length: {len(track.lyrics)}")
        if track.lyrics:
            print(f"lyrics[:500]:")
            print(f"  {track.lyrics[:500]}")
            # Проверим, есть ли искомые фразы
            lower = track.lyrics.lower()
            for phrase in ["двое против всех", "против всех", "двое"]:
                print(f"  содержит '{phrase}': {phrase in lower}")


if __name__ == "__main__":
    main()