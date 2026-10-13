import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["DEMUCS_DEVICE"] = "cpu"

from soundseek_core import AudioIndexer
from soundseek_core.ontology import Ontology


def main():
    ontology = Ontology()
    indexer = AudioIndexer(db_path="data/library", ontology=ontology)
    indexer.index_folder_light("data")


if __name__ == "__main__":
    main()