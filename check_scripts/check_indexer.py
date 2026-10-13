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

    print("\n--- Индексация ---")
    indexer.index_folder("data")

    print("\n--- Поиск по тексту ---")
    queries = [
        "calm piano music",
        "energetic rock",
        "sad slow melody",
    ]
    for q in queries:
        print(f"\nЗапрос: {q}")
        results = indexer.search_text(q, top_k=3)
        for track, score in results:
            print(f"  {score:.3f}  {track.id}")


if __name__ == "__main__":
    main()