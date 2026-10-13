from typing import List, Dict, Any
from .db import VectorDB
from .indexer import AudioIndexer
from .ontology import Ontology
from .rules import RuleEngine


class Searcher:
    def __init__(self, indexer: AudioIndexer, ontology: Ontology):
        self.indexer = indexer
        self.db = indexer.db
        self.ontology = ontology
        self.rules = RuleEngine(ontology)

    # ---------- Точное совпадение по метаданным ----------
    def _exact_metadata_match(self, query: str) -> List[tuple]:
        """Ищет треки, у которых в title/artist/id встречается фраза из запроса."""
        q = query.lower().strip()
        if len(q) < 3:
            return []
        matches = []
        for track in self.db.tracks:
            haystack = f"{track.title} {track.artist} {track.id}".lower()
            if q in haystack:
                matches.append((track, 1.0))
        return matches

    # ---------- Семантический поиск ----------
    def _semantic_search(self, query: str, top_k: int = 10) -> List[tuple]:
        """Поиск через CLAP (аудиоэмбеддинги) — возвращает кандидатов."""
        emb = self.indexer.get_query_text_embedding(query)
        return self.db.search_audio(emb, top_k)

    # ---------- Основной метод ----------
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Каскадный поиск:
        1. Точное совпадение по метаданным.
        2. Семантический поиск через CLAP.
        3. Объединение кандидатов.
        4. Применение правил и формирование объяснений.
        """
        # Шаг 1. Точное совпадение
        exact = self._exact_metadata_match(query)

        # Шаг 2. Семантический поиск
        semantic = self._semantic_search(query, top_k=max(top_k * 2, 10))

        # Шаг 3. Объединение — приоритет точным совпадениям
        seen_ids = set()
        candidates = []
        for track, score in exact:
            if track.id not in seen_ids:
                candidates.append((track, score))
                seen_ids.add(track.id)
        for track, score in semantic:
            if track.id not in seen_ids:
                candidates.append((track, score))
                seen_ids.add(track.id)

        # Шаг 4. Символьная обработка
        ranked = self.rules.apply(query, candidates)

        # Шаг 5. Формирование финального ответа
        results = []
        for r in ranked[:top_k]:
            track = r["track"]
            explanation_lines = []
            if track.id in [t.id for t, _ in exact]:
                explanation_lines.append("точное совпадение по метаданным")
            for hit in r["rule_hits"]:
                explanation_lines.append(hit.explanation)
            if not explanation_lines:
                explanation_lines.append("найден по семантической близости")

            results.append({
                "track": track,
                "base_score": round(r["base_score"], 4),
                "final_score": round(r["final_score"], 4),
                "explanations": explanation_lines,
                "rule_hits": r["rule_hits"],
            })

        return results

    def search_by_audio(self, audio_input, top_k: int = 5) -> List[Dict[str, Any]]:
        """Поиск по напеванию или аудиофрагменту.

        audio_input: путь к wav-файлу или numpy-массив (16 кГц моно).
        """
        import numpy as np
        import librosa

        # Если передан путь — загружаем аудио
        if isinstance(audio_input, (str, bytes)) or hasattr(audio_input, "read"):
            audio, _ = librosa.load(audio_input, sr=48000, mono=True)
        else:
            audio = np.asarray(audio_input, dtype="float32")

        # Получаем аудиоэмбеддинг запроса через CLAP
        query_emb = self.indexer.get_audio_embedding(audio)

        # Ищем ближайших соседей в аудиоиндексе
        candidates = self.db.search_audio(query_emb, top_k=top_k * 2)

        # Ранжируем через правила (объяснения будут краткими — только по звучанию)
        query_text = "[напевание]"
        ranked = self.rules.apply(query_text, candidates)

        results = []
        for r in ranked[:top_k]:
            track = r["track"]
            explanations = []
            for hit in r["rule_hits"]:
                explanations.append(hit.explanation)
            if not explanations:
                explanations.append(
                    f"найден по совпадению звучания (сходство {r['base_score']:.3f})"
                )
            results.append({
                "track": track,
                "base_score": round(r["base_score"], 4),
                "final_score": round(r["final_score"], 4),
                "explanations": explanations,
                "rule_hits": r["rule_hits"],
            })
        return results