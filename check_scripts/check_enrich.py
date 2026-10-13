import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["DEMUCS_DEVICE"] = "cpu"

from soundseek_core import AudioIndexer


def main():
    indexer = AudioIndexer(db_path="data/library")
    indexer.enrich_with_lyrics()


if __name__ == "__main__":
    main()