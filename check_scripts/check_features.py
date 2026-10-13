import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["DEMUCS_DEVICE"] = "cpu"

from soundseek_core import AudioIndexer


def main():
    indexer = AudioIndexer(db_path="data/library")

    print("\n" + "=" * 70)
    print("1. ПРОВЕРКА: что сохранено в базе")
    print("=" * 70)
    for i, track in enumerate(indexer.db.tracks, 1):
        print(f"\n[{i}] {track.id}")
        print(f"    has_vocal: {track.has_vocal}")
        print(f"    lyrics:    {track.lyrics[:120] + '...' if len(track.lyrics) > 120 else track.lyrics}")

    print("\n" + "=" * 70)
    print("2. ПРОВЕРКА: поиск через CLAP (аудиоэмбеддинги)")
    print("=" * 70)
    queries = ["lonely day", "весёлая песня", "тяжёлый рок", "грустная мелодия"]
    for q in queries:
        print(f"\nЗапрос (CLAP): {q}")
        results = indexer.search_text(q, top_k=3)
        for track, score in results:
            print(f"    {score:.3f}  {track.id}")

    print("\n" + "=" * 70)
    print("3. ПРОВЕРКА: поиск через MiniLM (текстовые эмбеддинги)")
    print("=" * 70)
    for q in queries:
        print(f"\nЗапрос (MiniLM): {q}")
        emb = indexer.get_text_embedding(q)
        results = indexer.db.search_text(emb, top_k=3)
        for track, score in results:
            print(f"    {score:.3f}  {track.id}")

    print("\n" + "=" * 70)
    print("4. ПРОВЕРКА: поиск по строкам из песни")
    print("=" * 70)
    # Строки, которые точно есть в распознанных текстах
    lyric_queries = ["lonely day", "should be banned", "двое против всех", "бал лицемеров"]
    for q in lyric_queries:
        print(f"\nЗапрос по строке: {q}")
        emb = indexer.get_text_embedding(q)
        results = indexer.db.search_text(emb, top_k=3)
        for track, score in results:
            print(f"    {score:.3f}  {track.id}")


if __name__ == "__main__":
    main()