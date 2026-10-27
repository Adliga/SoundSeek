"""Лёгкая онтология жанров и настроений.

Онтология хранится в JSON и используется в трёх местах:
1) разбор запроса и подсказки из имён файлов;
2) иерархические отношения для правил;
3) объяснения вида «hard_rock является поджанром rock».

Ключевое отличие от первой версии: ключевые слова ищутся по границам слов
и по принципу «самое длинное совпадение», а не как произвольные подстроки.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Optional

from .config import ONTOLOGY_PATH


def normalize_text(text: str) -> str:
    """Нормализация для поиска: регистр, ё, подчёркивания и дефисы."""
    text = (text or "").lower().replace("ё", "е")
    text = text.replace("_", " ").replace("-", " ").replace("/", " ")
    text = text.replace("\\", " ")
    text = re.sub(r"[^\w\s&]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


_RU_ENDINGS = (
    "ами", "ями", "ого", "его", "ому", "ему", "ыми", "ими",
    "ая", "яя", "ое", "ее", "ые", "ие", "ой", "ей", "ый", "ий",
    "а", "я", "о", "е", "ы", "и", "у", "ю", "ь",
)


def stem_word(word: str) -> str:
    """Очень простой стеммер для русской морфологии.

    Он не претендует на лингвистическую точность, но убирает наиболее
    частые падежные окончания и позволяет ``панка`` найти ``панк``,
    а ``грустного`` — ``грустный``.
    """
    word = normalize_text(word)
    if len(word) <= 4:
        return word
    for ending in _RU_ENDINGS:
        if word.endswith(ending) and len(word) - len(ending) >= 3:
            return word[: -len(ending)]
    if word.endswith("s") and len(word) > 4:
        return word[:-1]
    return word


class Ontology:
    def __init__(self, path: str | Path = ONTOLOGY_PATH):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.path = Path(path)
        self.genres: dict[str, dict] = data["genres"]
        self.moods: dict[str, dict] = data["moods"]
        self.keywords: dict[str, list[str]] = data["keywords"]
        self.prompts: dict = data.get("prompts", {})
        self.content_types: dict[str, str] = data.get("content_types", {})

        self._concept_words: list[tuple[str, str, str]] = []
        self._phrase_words: list[tuple[str, str, str]] = []
        self._word_index: dict[str, list[tuple[str, str]]] = {}
        for concept, words in self.keywords.items():
            for word in words:
                normalized = normalize_text(word)
                if not normalized:
                    continue
                kind = "genre" if concept in self.genres else "mood"
                self._concept_words.append((normalized, concept, kind))
                if " " in normalized or "&" in normalized:
                    self._phrase_words.append((normalized, concept, kind))
                else:
                    self._word_index.setdefault(stem_word(normalized), []).append(
                        (concept, kind)
                    )
        # Длинные фразы должны проверяться раньше коротких.
        self._concept_words.sort(key=lambda item: (-len(item[0]), item[0]))
        self._phrase_words.sort(key=lambda item: (-len(item[0]), item[0]))

        self._keyword_to_concept = {
            word: concept for word, concept, _ in self._concept_words
        }

    def _lookup_concept(self, word: str) -> str:
        normalized = normalize_text(word)
        concept = self._keyword_to_concept.get(normalized)
        if concept:
            return concept
        matches = self._word_index.get(stem_word(normalized), [])
        # При коллизии основ предпочитаем жанр.
        for candidate, kind in matches:
            if kind == "genre":
                return candidate
        return matches[0][0] if matches else ""

    # ---------- Жанры ----------
    def get_genre_ancestors(self, genre: str) -> list[str]:
        """Возвращает [сам жанр, родитель, дед, ...]."""
        result: list[str] = []
        current: Optional[str] = genre
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            result.append(current)
            current = self.genres.get(current, {}).get("parent")
        return result

    def genre_depth(self, genre: str) -> int:
        return max(0, len(self.get_genre_ancestors(genre)) - 1)

    def genre_distance(self, g1: str, g2: str) -> Optional[int]:
        """Расстояние по общему предку; None, если жанры не связаны."""
        a = self.get_genre_ancestors(g1)
        b = self.get_genre_ancestors(g2)
        if not a or not b or not g1 or not g2:
            return None
        common = set(a) & set(b)
        if not common:
            return None
        return min(a.index(x) + b.index(x) for x in common)

    def is_genre_related(self, g1: str, g2: str) -> bool:
        """Родственными считаем жанры на расстоянии не более двух шагов."""
        distance = self.genre_distance(g1, g2)
        return distance is not None and distance <= 2

    def is_genre_within(self, genre: str, ancestor: str) -> bool:
        """Проверяет, что genre — сам ancestor или его потомок.

        Нужно для отрицаний: «не панк» исключает punk_rock и его поджанры,
        но не heavy_metal, который тоже находится под rock.
        """
        return bool(genre and ancestor and ancestor in self.get_genre_ancestors(genre))

    def genre_matches(self, track_genre: str, query_genre: str) -> bool:
        """Совместимы ли жанр трека и жанр запроса.

        Совместимость направленная: запрос «rock» покрывает hard_rock,
        запрос «punk» не покрывает indie_rock, хотя оба являются детьми
        rock. Если трек размечен более общим жанром, чем запрос, это
        допускается как менее точное совпадение.
        """
        if not track_genre or not query_genre:
            return False
        return self.is_genre_within(
            track_genre, query_genre
        ) or self.is_genre_within(query_genre, track_genre)

    def describe_genre_relation(self, query_genre: str, track_genre: str) -> str:
        if query_genre == track_genre:
            return f"точное совпадение жанра ({track_genre})"
        a = self.get_genre_ancestors(track_genre)
        b = self.get_genre_ancestors(query_genre)
        common = set(a) & set(b)
        if common:
            ancestor = min(common, key=lambda x: a.index(x) + b.index(x))
            return f"{track_genre} и {query_genre} связаны через {ancestor}"
        return f"{track_genre} не связан с {query_genre}"

    def get_related_moods(self, genre: str) -> set[str]:
        moods: set[str] = set()
        for g in self.get_genre_ancestors(genre):
            moods.update(self.genres.get(g, {}).get("related_moods", []))
        return moods

    # ---------- Настроения ----------
    def get_mood_ancestors(self, mood: str) -> list[str]:
        result: list[str] = []
        current: Optional[str] = mood
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            result.append(current)
            current = self.moods.get(current, {}).get("parent")
        return result

    def mood_distance(self, m1: str, m2: str) -> Optional[int]:
        a = self.get_mood_ancestors(m1)
        b = self.get_mood_ancestors(m2)
        if not a or not b or not m1 or not m2:
            return None
        common = set(a) & set(b)
        if not common:
            return None
        return min(a.index(x) + b.index(x) for x in common)

    def is_mood_related(self, m1: str, m2: str) -> bool:
        distance = self.mood_distance(m1, m2)
        return distance is not None and distance <= 2

    def is_mood_within(self, mood: str, ancestor: str) -> bool:
        return bool(mood and ancestor and ancestor in self.get_mood_ancestors(mood))

    def get_related_genres(self, mood: str) -> set[str]:
        genres: set[str] = set()
        for m in self.get_mood_ancestors(mood):
            genres.update(self.moods.get(m, {}).get("related_genres", []))
        return genres

    def mood_is_consistent_with_genre(self, mood: str, genre: str) -> bool:
        related = self.get_related_moods(genre)
        if not related:
            return True
        if mood in related:
            return True
        return any(self.is_mood_related(mood, other) for other in related)

    # ---------- Разбор запроса ----------
    def extract_concepts(self, query: str) -> dict[str, list[str]]:
        """Возвращает жанры и настроения с учётом границ слов и морфологии.

        Сначала ищутся самые длинные фразы (``pop punk``, ``drum and bass``),
        затем отдельные слова по нормализованной основе. Совпадение
        маскируется, поэтому ``trap`` не порождает ``rap``, а ``synthpop`` —
        ``pop``.
        """
        text = normalize_text(query)
        masked = text
        genres: list[str] = []
        moods: list[str] = []

        for word, concept, kind in self._phrase_words:
            pattern = rf"(?<!\w){re.escape(word)}(?!\w)"
            while True:
                match = re.search(pattern, masked)
                if not match:
                    break
                if kind == "genre":
                    genres.append(concept)
                else:
                    moods.append(concept)
                masked = (
                    masked[: match.start()]
                    + " " * (match.end() - match.start())
                    + masked[match.end():]
                )

        for token in re.findall(r"[\w&]+", masked, flags=re.UNICODE):
            for concept, kind in self._word_index.get(stem_word(token), []):
                if kind == "genre":
                    genres.append(concept)
                else:
                    moods.append(concept)

        return {
            "genres": sorted(set(genres)),
            "moods": sorted(set(moods)),
        }

    def map_genre_value(self, value: str) -> str:
        """Нормализует свободный жанровый тег в понятие онтологии.

        Поддерживает значения вида ``Punk;Rock``, ``Rock/Pop``, ``Heavy Metal``.
        """
        if not value:
            return ""
        whole = normalize_text(value)
        candidates: list[str] = []
        for part in re.split(r"[;,/|]+", value):
            normalized = normalize_text(part)
            if not normalized:
                continue
            concept = self._lookup_concept(normalized)
            if concept in self.genres:
                candidates.append(concept)
                continue
            # Иногда тег содержит несколько слов без разделителя.
            concepts = self.extract_concepts(part)["genres"]
            candidates.extend(concepts)
        concept = self._lookup_concept(whole)
        if concept in self.genres:
            candidates.append(concept)
        if not candidates:
            return ""
        # Более специфичный (глубокий) жанр важнее общего.
        return max(
            sorted(set(candidates)),
            key=lambda item: (self.genre_depth(item), len(item)),
        )

    # ---------- Промпты для zero-shot ----------
    def get_genre_prompts(self) -> dict[str, str]:
        return self.prompts.get("genres", {})

    def get_mood_prompts(self) -> dict[str, str]:
        return self.prompts.get("moods", {})

    def get_content_type_prompts(self) -> dict[str, str]:
        return self.content_types

    def get_flat_genre_prompts(self) -> dict[str, str]:
        """Все жанры, для которых есть промпт (32 класса в текущей онтологии)."""
        sub_prompts = self.prompts.get("subgenres", {})
        return {
            genre: sub_prompts[genre]
            for genre in self.genres
            if genre in sub_prompts
        }

    # Совместимость со старым названием.
    def get_all_leaf_prompts(self) -> dict[str, str]:
        return self.get_flat_genre_prompts()

    def get_genre_prompt(self, genre: str) -> str:
        return (
            self.prompts.get("subgenres", {}).get(genre)
            or self.prompts.get("genres", {}).get(genre)
            or genre.replace("_", " ")
        )

    def get_mood_prompt(self, mood: str) -> str:
        return self.prompts.get("moods", {}).get(mood) or mood.replace("_", " ")

    # ---------- Представление ----------
    @property
    def genre_names(self) -> list[str]:
        return sorted(self.genres)

    @property
    def mood_names(self) -> list[str]:
        return sorted(self.moods)

    def all_prompt_words(self) -> Iterable[str]:
        for words in self.keywords.values():
            yield from words
