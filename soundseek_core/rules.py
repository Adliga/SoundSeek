"""Правила предметной области поверх результатов поиска.

Правила работают с нормализованным жанром ``track.derived.genre``, а не с
сырым тегом ``Punk;Rock``. Это устраняет ложные конфликты и делает
объяснения воспроизводимыми.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

from rapidfuzz import fuzz

from .models import ParsedQuery, SearchHit, Track
from .ontology import Ontology, normalize_text, stem_word
from .query_parser import parse_query

STOP_WORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "at", "is", "it",
    "this", "that", "for", "with", "by", "from",
    "и", "в", "во", "на", "с", "со", "к", "по", "из", "от", "для", "не",
    "но", "а", "или", "же", "бы", "ли", "что", "как", "это", "то",
    "music", "музыка", "song", "песня", "track", "трек", "audio", "аудио",
    "official", "video", "видео", "lyrics", "текст", "topic", "hd", "mv",
}

MIN_WORD_LEN = 2


@dataclass
class RuleResult:
    rule_name: str
    score_delta: float
    explanation: str


def tokenize(text: str) -> list[str]:
    text = normalize_text(text)
    return [
        token
        for token in re.findall(r"[\w&]+", text, flags=re.UNICODE)
        if len(token) >= MIN_WORD_LEN and token not in STOP_WORDS
    ]


def _tokens_match(left: str, right: str) -> bool:
    if left == right:
        return True
    if stem_word(left) == stem_word(right):
        return True
    if min(len(left), len(right)) >= 4 and fuzz.ratio(left, right) >= 88:
        return True
    return False


def _token_in(token: str, haystack: Iterable[str]) -> bool:
    return any(_tokens_match(token, candidate) for candidate in haystack)


def _phrase_in(phrase: str, haystack: str) -> bool:
    if not phrase:
        return False
    return phrase in haystack


class RuleEngine:
    def __init__(self, ontology: Ontology):
        self.ontology = ontology

    # ---------- Публичный интерфейс ----------
    def apply(
        self,
        query: ParsedQuery | str,
        candidates: list[tuple],
    ) -> list[SearchHit]:
        """Применяет правила и возвращает отсортированные результаты.

        Поддерживает старый вызов ``apply("рок", [(track, score), ...])``.
        """
        if isinstance(query, str):
            parsed = parse_query(query, self.ontology)
        else:
            parsed = query

        hits: list[SearchHit] = []
        for order, candidate in enumerate(candidates):
            track = candidate[0]
            base_score = float(candidate[1])
            channels = candidate[2] if len(candidate) > 2 and isinstance(candidate[2], dict) else {}
            ranks = candidate[3] if len(candidate) > 3 and isinstance(candidate[3], dict) else {}

            allowed, filter_hit = self._hard_filter(parsed, track)
            if not allowed:
                continue

            rule_hits: list[RuleResult] = []
            if filter_hit is not None:
                rule_hits.append(filter_hit)
            for result in (
                self._genre_rule(parsed, track),
                self._mood_rule(parsed, track),
                self._metadata_rule(parsed, track),
                self._lyrics_rule(parsed, track),
                self._genre_conflict_rule(parsed, track),
            ):
                if result is not None:
                    rule_hits.append(result)

            delta = sum(result.score_delta for result in rule_hits)
            final_score = max(0.0, min(1.0, base_score + delta))
            explanations = [
                result.explanation for result in rule_hits if result.explanation
            ]
            hits.append(
                SearchHit(
                    track=track,
                    base_score=round(base_score, 4),
                    final_score=round(final_score, 4),
                    explanations=explanations,
                    rule_hits=rule_hits,
                    channels=channels,
                    channel_ranks=ranks,
                    rank=order,
                )
            )
        hits.sort(key=lambda hit: (-hit.final_score, hit.rank))
        return hits

    # ---------- Фильтры ----------
    def _hard_filter(
        self, query: ParsedQuery, track: Track
    ) -> tuple[bool, Optional[RuleResult]]:
        genre = track.effective_genre or self.ontology.map_genre_value(track.tags.genre)

        if (
            query.genres
            or query.moods
            or query.negated_genres
            or query.negated_moods
        ) and track.derived.content_type not in (
            "",
            "music",
            "singing",
        ):
            return False, None

        if query.genres and genre and not any(
            self.ontology.genre_matches(genre, candidate)
            for candidate in query.genres
        ):
            # Известный, но несовместимый жанр не должен попадать в выдачу
            # только за счёт общего CLAP-сходства.
            return False, None

        if (
            query.moods
            and track.derived.mood
            and not any(
                self.ontology.is_mood_related(mood, track.derived.mood)
                for mood in query.moods
            )
            and not self._metadata_mentions(track, query)
        ):
            # Настроение zero-shot менее надёжно, но известное
            # несовместимое настроение всё равно нельзя выдавать за
            # выполнение запроса. Исключение — точное название или
            # исполнитель: «Lonely Day» остаётся названием, даже если
            # классификатор ошибочно назвал трек весёлым.
            return False, None

        for negated in query.negated_genres:
            if genre and self.ontology.is_genre_within(genre, negated):
                return False, None
        for negated in query.negated_moods:
            if track.derived.mood and self.ontology.is_mood_within(
                track.derived.mood, negated
            ):
                return False, None

        if query.has_vocal is not None and track.derived.content_type not in (
            "",
            "music",
            "singing",
        ):
            return False, None
        if query.has_vocal is not None and track.derived.has_vocal is None:
            # Неизвестный вокал нельзя считать ни «есть», ни «нет»:
            # иначе фильтр «без вокала» показывает непроверенные треки.
            return False, None
        if query.has_vocal is False and track.derived.has_vocal is True:
            return False, None
        if query.has_vocal is True and track.derived.has_vocal is False:
            return False, None

        if query.year_from is not None or query.year_to is not None:
            year = track.tags.year
            if year is None:
                # Запрос по году должен опираться на известный год, а не
                # молча включать все треки без метаданных.
                return False, None
            if query.year_from is not None and year < query.year_from:
                return False, None
            if query.year_to is not None and year > query.year_to:
                return False, None

        if query.artist:
            metadata = " ".join(
                [track.tags.artist, track.tags.album_artist, track.display_title]
            )
            artist_tokens = tokenize(query.artist)
            metadata_tokens = tokenize(metadata)
            if artist_tokens and not all(
                _token_in(token, metadata_tokens) for token in artist_tokens
            ):
                return False, None
        return True, None

    def _metadata_mentions(self, track: Track, query: ParsedQuery) -> bool:
        text = normalize_text(query.artist or query.free_text)
        if not text:
            return False
        haystack = normalize_text(
            " ".join(
                [
                    track.tags.title,
                    track.tags.artist,
                    track.tags.album,
                    track.display_title,
                ]
            )
        )
        return bool(haystack) and text in haystack

    # ---------- Жанр ----------
    def _genre_rule(self, query: ParsedQuery, track: Track) -> Optional[RuleResult]:
        if not query.genres:
            return None
        genre = track.effective_genre or self.ontology.map_genre_value(track.tags.genre)
        if not genre:
            return None
        best: tuple[str, int, str] | None = None
        for candidate in query.genres:
            if self.ontology.is_genre_within(genre, candidate):
                distance = self.ontology.genre_distance(candidate, genre)
                relation = "track_within_query"
            elif self.ontology.is_genre_within(candidate, genre):
                distance = 1
                relation = "query_within_track"
            else:
                continue
            if best is None or distance < best[1]:
                best = (candidate, distance, relation)
        if best is None:
            return None
        candidate, distance, relation = best
        if relation == "query_within_track":
            # Трек размечен более общим жанром; это допустимо, но слабее
            # точного или более специфичного совпадения.
            delta = 0.10
        elif distance == 0:
            delta = 0.45
        elif distance == 1:
            delta = 0.22
        elif distance == 2:
            delta = 0.12
        else:
            return None
        source = track.derived.genre_source or "вычислено"
        return RuleResult(
            "genre_match",
            delta,
            f"жанр {genre} соответствует запросу {candidate} "
            f"({self.ontology.describe_genre_relation(candidate, genre)}; "
            f"источник: {source})",
        )

    # ---------- Настроение ----------
    def _mood_rule(self, query: ParsedQuery, track: Track) -> Optional[RuleResult]:
        if not query.moods or not track.derived.mood:
            return None
        best: tuple[str, int] | None = None
        for candidate in query.moods:
            distance = self.ontology.mood_distance(candidate, track.derived.mood)
            if distance is not None:
                if best is None or distance < best[1]:
                    best = (candidate, distance)
        if best is None:
            return None
        candidate, distance = best
        delta = 0.20 if distance == 0 else 0.10
        return RuleResult(
            "mood_match",
            delta,
            f"настроение {track.derived.mood} соответствует запросу {candidate}",
        )

    # ---------- Метаданные ----------
    def _metadata_rule(self, query: ParsedQuery, track: Track) -> Optional[RuleResult]:
        text = query.artist or query.free_text
        tokens = tokenize(text)
        if not tokens:
            return None
        # Намеренно не используем полный путь: иначе слово music в названии
        # папки Music Video повышает все треки.
        metadata = " ".join(
            [
                track.tags.title,
                track.tags.artist,
                track.tags.album,
                track.tags.album_artist,
                track.tags.composer,
                track.tags.comment,
                track.stem,
            ]
        )
        metadata_norm = normalize_text(metadata)
        metadata_tokens = tokenize(metadata)
        for size in (min(3, len(tokens)), 2):
            if size < 2 or len(tokens) < size:
                continue
            for i in range(len(tokens) - size + 1):
                phrase = " ".join(tokens[i : i + size])
                if _phrase_in(phrase, metadata_norm):
                    return RuleResult(
                        "metadata_match",
                        0.12,
                        f"фраза «{phrase}» найдена в метаданных",
                    )
        matched = [token for token in tokens if _token_in(token, metadata_tokens)]
        if matched:
            return RuleResult(
                "metadata_match",
                min(0.10, 0.04 * len(matched)),
                "совпадение по метаданным: " + ", ".join(matched[:4]),
            )
        return None

    # ---------- Текст песни ----------
    def _lyrics_rule(self, query: ParsedQuery, track: Track) -> Optional[RuleResult]:
        if not track.derived.lyrics:
            return None
        tokens = tokenize(query.free_text)
        if not tokens:
            return None
        lyrics_norm = normalize_text(track.derived.lyrics)
        lyrics_tokens = tokenize(track.derived.lyrics)
        for size in (min(3, len(tokens)), 2):
            if size < 2 or len(tokens) < size:
                continue
            for i in range(len(tokens) - size + 1):
                phrase = " ".join(tokens[i : i + size])
                if _phrase_in(phrase, lyrics_norm):
                    return RuleResult(
                        "lyrics_match",
                        0.15,
                        f"фраза «{phrase}» найдена в тексте песни",
                    )
        matched = [token for token in tokens if _token_in(token, lyrics_tokens)]
        if matched:
            return RuleResult(
                "lyrics_match",
                min(0.10, 0.03 * len(matched)),
                "совпадение по тексту песни: " + ", ".join(matched[:4]),
            )
        return None

    # ---------- Конфликт ----------
    def _genre_conflict_rule(
        self, query: ParsedQuery, track: Track
    ) -> Optional[RuleResult]:
        if not query.genres:
            return None
        genre = track.effective_genre or self.ontology.map_genre_value(track.tags.genre)
        if not genre:
            return None
        if any(
            self.ontology.genre_matches(genre, candidate)
            for candidate in query.genres
        ):
            return None
        candidate = query.genres[0]
        return RuleResult(
            "genre_conflict",
            -0.25,
            f"жанр трека {genre} не соответствует запросу {candidate}",
        )
