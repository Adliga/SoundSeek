from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional, Set
import re

from .models import Track
from .ontology import Ontology


# Стоп-слова: не учитываем при сравнении
STOP_WORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "at", "is", "it",
    "this", "that", "for", "with", "by", "from",
    "и", "в", "во", "на", "с", "со", "к", "по", "из", "от", "для", "не",
    "но", "а", "или", "же", "бы", "ли", "что", "как", "это", "то",
}

MIN_WORD_LEN = 3


@dataclass
class RuleResult:
    rule_name: str
    score_delta: float
    explanation: str


@dataclass
class Rule:
    name: str
    condition: Callable
    action: Callable


def _tokenize(text: str) -> List[str]:
    """Разбивает текст на слова, убирает пунктуацию, приводит к нижнему регистру."""
    text = text.lower()
    text = re.sub(r"[^\w\s\-]", " ", text, flags=re.UNICODE)
    words = [w for w in text.split() if len(w) >= MIN_WORD_LEN and w not in STOP_WORDS]
    return words


def _extract_phrases(words: List[str], n: int = 2) -> List[str]:
    """Возвращает список n-грамм (фраз из n слов подряд)."""
    if len(words) < n:
        return []
    return [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]


def _prefix_match(word: str, target: str, min_prefix: int = 4) -> bool:
    """Проверяет, есть ли у двух слов общий префикс (упрощённая морфология)."""
    if len(word) < min_prefix or len(target) < min_prefix:
        return word == target
    return word[:min_prefix] == target[:min_prefix]


def _word_in_text(word: str, haystack_words: Set[str]) -> bool:
    """Ищет слово в тексте с учётом префиксов."""
    if word in haystack_words:
        return True
    return any(_prefix_match(word, hw) for hw in haystack_words)


class RuleEngine:
    def __init__(self, ontology: Ontology):
        self.ontology = ontology
        self.rules: List[Rule] = []
        self._register_default_rules()

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def apply(
        self,
        query: str,
        candidates: List[tuple],
    ) -> List[dict]:
        concepts = self.ontology.extract_concepts(query)
        results = []

        for track, base_score in candidates:
            hits: List[RuleResult] = []
            delta = 0.0
            filtered = False

            for rule in self.rules:
                if not rule.condition(query, track, concepts, self.ontology):
                    continue
                res = rule.action(query, track, concepts, self.ontology)
                if res is None:
                    continue
                if res.score_delta == float("-inf"):
                    filtered = True
                    hits.append(res)
                    break
                delta += res.score_delta
                hits.append(res)

            if filtered:
                continue

            results.append({
                "track": track,
                "base_score": base_score,
                "final_score": base_score + delta,
                "rule_hits": hits,
            })

        results.sort(key=lambda r: r["final_score"], reverse=True)
        return results

    # ---------- Правила ----------
    def _register_default_rules(self) -> None:
        self.add_rule(Rule("genre_match", self._genre_in_query, self._boost_on_genre_match))
        self.add_rule(Rule("mood_match", self._mood_in_query, self._boost_on_mood_match))
        self.add_rule(Rule("metadata_match", self._query_in_metadata, self._boost_on_metadata))
        self.add_rule(Rule("lyrics_match", self._query_in_lyrics, self._boost_on_lyrics))
        self.add_rule(Rule("genre_conflict", self._genre_conflict, self._penalty_on_genre_conflict))

    # ---------- Жанр ----------
    @staticmethod
    def _genre_in_query(query, track, concepts, ontology) -> bool:
        return bool(concepts["genres"]) and bool(track.genre)

    def _boost_on_genre_match(self, query, track, concepts, ontology):
        for g in concepts["genres"]:
            if ontology.is_genre_related(g, track.genre):
                return RuleResult(
                    rule_name="genre_match",
                    score_delta=0.30,
                    explanation=f"совпадение по жанру ({track.genre} ~ {g})",
                )
        return None

    # ---------- Настроение ----------
    @staticmethod
    def _mood_in_query(query, track, concepts, ontology) -> bool:
        return bool(concepts["moods"]) and bool(track.mood)

    def _boost_on_mood_match(self, query, track, concepts, ontology):
        for m in concepts["moods"]:
            if m == track.mood:
                return RuleResult(
                    rule_name="mood_match",
                    score_delta=0.20,
                    explanation=f"совпадение по настроению ({m})",
                )
            if m in ontology.moods.get(track.mood, {}).get("children", []) \
               or track.mood in ontology.moods.get(m, {}).get("children", []):
                return RuleResult(
                    rule_name="mood_match",
                    score_delta=0.10,
                    explanation=f"близкое настроение ({track.mood} ~ {m})",
                )
        return None

    # ---------- Метаданные ----------
    @staticmethod
    def _query_in_metadata(query, track, concepts, ontology) -> bool:
        # Быстрая проверка: есть ли вообще что-то осмысленное в запросе
        return len(_tokenize(query)) > 0

    def _boost_on_metadata(self, query, track, concepts, ontology):
        query_words = _tokenize(query)
        if not query_words:
            return None

        # Метаданные: имя файла + путь + поля
        meta_text = f"{track.id} {track.title} {track.artist} {track.album} {track.path}"
        meta_words = set(_tokenize(meta_text))

        # 1. Фразы по 2 слова
        phrases = _extract_phrases(query_words, n=2)
        for phrase in phrases:
            if phrase in meta_text.lower():
                return RuleResult(
                    rule_name="metadata_match",
                    score_delta=0.50,
                    explanation=f"совпадение по метаданным (фраза: «{phrase}»)",
                )

        # 2. Отдельные слова
        matched = [w for w in query_words if _word_in_text(w, meta_words)]
        if matched:
            return RuleResult(
                rule_name="metadata_match",
                score_delta=0.35,
                explanation=f"совпадение по метаданным ({', '.join(matched)})",
            )
        return None

    # ---------- Текст песни ----------
    @staticmethod
    def _query_in_lyrics(query, track, concepts, ontology) -> bool:
        if not track.lyrics:
            return False
        return len(_tokenize(query)) > 0

    def _boost_on_lyrics(self, query, track, concepts, ontology):
        if not track.lyrics:
            return None

        query_words = _tokenize(query)
        if not query_words:
            return None

        lyrics_lower = track.lyrics.lower()
        lyrics_words = set(_tokenize(track.lyrics))

        # 1. Фразы по 2 слова
        phrases = _extract_phrases(query_words, n=2)
        for phrase in phrases:
            if phrase in lyrics_lower:
                return RuleResult(
                    rule_name="lyrics_match",
                    score_delta=0.40,
                    explanation=f"совпадение по тексту песни (фраза: «{phrase}»)",
                )

        # 2. Отдельные слова
        matched = [w for w in query_words if _word_in_text(w, lyrics_words)]
        if matched:
            return RuleResult(
                rule_name="lyrics_match",
                score_delta=0.25,
                explanation=f"совпадение по тексту песни ({', '.join(matched)})",
            )
        return None

    # ---------- Конфликт жанров ----------
    @staticmethod
    def _genre_conflict(query, track, concepts, ontology) -> bool:
        return bool(concepts["genres"]) and bool(track.genre) \
               and not ontology.is_genre_related(concepts["genres"][0], track.genre)

    def _penalty_on_genre_conflict(self, query, track, concepts, ontology):
        return RuleResult(
            rule_name="genre_conflict",
            score_delta=-0.20,
            explanation=f"жанр трека ({track.genre}) не соответствует запросу ({concepts['genres'][0]})",
        )