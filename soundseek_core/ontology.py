import json
from pathlib import Path
from typing import List, Set


class Ontology:
    def __init__(self, path: str = "soundseek_core/knowledge/ontology.json"):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.genres = data["genres"]
        self.moods = data["moods"]
        self.keywords = data["keywords"]
        self.prompts = data.get("prompts", {"genres": {}, "moods": {}})
        self.content_types = data.get("content_types", {})

        self._keyword_to_concept = {}
        for concept, words in self.keywords.items():
            for w in words:
                self._keyword_to_concept[w.lower()] = concept

    # ---------- Работа с жанрами ----------
    def get_genre_ancestors(self, genre: str) -> List[str]:
        result = [genre]
        current = self.genres.get(genre, {})
        while current.get("parent"):
            parent = current["parent"]
            result.append(parent)
            current = self.genres.get(parent, {})
        return result

    def is_genre_related(self, g1: str, g2: str) -> bool:
        if g1 == g2:
            return True
        return g2 in self.get_genre_ancestors(g1) or g1 in self.get_genre_ancestors(g2)

    def get_related_moods(self, genre: str) -> Set[str]:
        moods = set()
        for g in self.get_genre_ancestors(genre):
            moods.update(self.genres.get(g, {}).get("related_moods", []))
        return moods

    # ---------- Работа с настроениями ----------
    def get_related_genres(self, mood: str) -> Set[str]:
        genres = set()
        current = mood
        while current:
            genres.update(self.moods.get(current, {}).get("related_genres", []))
            parent = self.moods.get(current, {}).get("parent")
            current = parent
        return genres

    # ---------- Разбор запроса ----------
    def extract_concepts(self, query: str) -> dict:
        query_lower = query.lower()
        found_genres = set()
        found_moods = set()

        for word, concept in self._keyword_to_concept.items():
            if word in query_lower:
                if concept in self.genres:
                    found_genres.add(concept)
                elif concept in self.moods:
                    found_moods.add(concept)

        return {
            "genres": list(found_genres),
            "moods": list(found_moods),
        }

    # ---------- Гипотезы для zero-shot классификации ----------
    def get_genre_prompts(self) -> dict:
        return self.prompts.get("genres", {})

    def get_mood_prompts(self) -> dict:
        return self.prompts.get("moods", {})

    def get_content_type_prompts(self) -> dict:
        return self.content_types

    def get_all_leaf_prompts(self) -> dict:
        """Возвращает плоский словарь всех поджанров (листьев дерева)."""
        leaves = {}
        sub_prompts = self.prompts.get("subgenres", {})
        for genre, info in self.genres.items():
            # Если у жанра есть промпт и это лист (или мы хотим использовать его как конечный класс)
            if genre in sub_prompts:
                leaves[genre] = sub_prompts[genre]
        return leaves