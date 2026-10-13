import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["DEMUCS_DEVICE"] = "cpu"

from soundseek_core import AudioIndexer
from soundseek_core.ontology import Ontology
from soundseek_core.searcher import Searcher


def main():
    indexer = AudioIndexer(db_path="data/library")
    ontology = Ontology()
    searcher = Searcher(indexer, ontology)

    queries = [
        "lonely day",
        "грустный рок",
        "piano",
        "весёлый панк",
        "ambient calm music",
        "тяжёлый метал",
        "Двое против всех",
        "этот мир",
    ]

    for q in queries:
        print("\n" + "=" * 70)
        print(f"Запрос: {q}")
        print("=" * 70)
        results = searcher.search(q, top_k=3)
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