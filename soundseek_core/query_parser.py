"""Разбор пользовательского запроса на структурированные признаки.

Парсер не пытается понять язык целиком. Он выделяет то, что умеет
онтология: жанры, настроения, отрицания, вокал, годы и исполнителя.
Остальной текст остаётся свободным запросом для лексического и
семантического каналов.
"""

from __future__ import annotations

import re

from .models import ParsedQuery
from .ontology import Ontology

_NEGATION_RE = re.compile(
    r"(?<!\w)(не|без|not|without|кроме|except)(?!\w)\s+([^,;.!?]+)",
    flags=re.IGNORECASE,
)
_VOCAL_RE = re.compile(
    r"(?<!\w)(вокал\w*|с вокалом|со вокалом|a cappella|а капелла)(?!\w)",
    flags=re.IGNORECASE,
)
_INSTRUMENTAL_RE = re.compile(
    r"(?<!\w)(без вокала|without vocals|инструментал\w*|instrumental)(?!\w)",
    flags=re.IGNORECASE,
)
_NO_INSTRUMENTAL_RE = re.compile(
    r"(?<!\w)no instrumental(?!\w)",
    flags=re.IGNORECASE,
)
_NO_VOCALS_RE = re.compile(
    r"(?<!\w)no vocals?(?!\w)",
    flags=re.IGNORECASE,
)
_YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")
_LONG_DECADE_RE = re.compile(
    r"(?<!\d)((?:19|20)\d{2})\s*[- ]?\s*(?:х|е|ые|ых|s|'s)(?!\w)",
    flags=re.IGNORECASE,
)
_DECADE_RE = re.compile(
    r"(?<!\d)(\d{2})\s*[- ]?\s*(?:х|е|ые|ых|s|'s)(?!\w)",
    flags=re.IGNORECASE,
)
_WORD_DECADES = {
    "сороковые": 1940,
    "пятидесятые": 1950,
    "шестидесятые": 1960,
    "семидесятые": 1970,
    "восьмидесятые": 1980,
    "девяностые": 1990,
    "нулевые": 2000,
    "двухтысячные": 2000,
    "десятые": 2010,
}
_ARTIST_RE = re.compile(
    r"(?<!\w)(?:исполнитель|артист|artist|by)\s+([^,;.!?]+)",
    flags=re.IGNORECASE,
)
_QUOTED_RE = re.compile(r"[\"«“]([^\"»”]{2,80})[\"»”]")


def _strip_negation_tail(chunk: str) -> str:
    """Обрезает отрицание на союзе: «не панк, а рок» -> «панк»."""
    return re.split(r"\b(?:а|но|and|but)\b", chunk, maxsplit=1, flags=re.IGNORECASE)[0]


def _negated_spans(query: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for match in _NEGATION_RE.finditer(query):
        chunk = _strip_negation_tail(match.group(2))
        # Конец считаем от начала второго группы, а не от длины слова
        # отрицания: между ними может быть несколько пробелов.
        end = match.start(2) + len(chunk)
        spans.append((match.start(), end, chunk))
    return spans


def parse_query(raw: str, ontology: Ontology) -> ParsedQuery:
    raw = (raw or "").strip()
    query = ParsedQuery(raw=raw, free_text=raw)
    if not raw:
        return query

    # 1. Отрицания. Сначала вырезаем их из положительной части запроса.
    masked_chars = list(raw)
    for start, end, chunk in _negated_spans(raw):
        for i in range(start, min(end, len(masked_chars))):
            masked_chars[i] = " "
        # «не инструментал» и «без инструментала» означают вокал, а
        # «не вокал» и «без вокала» — отсутствие вокала.
        if _NO_INSTRUMENTAL_RE.search(chunk):
            query.has_vocal = True
        elif _NO_VOCALS_RE.search(chunk):
            query.has_vocal = False
        elif _INSTRUMENTAL_RE.search(chunk):
            query.has_vocal = True
        elif re.search(
            r"\b(?:вокал\w*|vocals?|singing|a cappella)\b",
            chunk,
            re.IGNORECASE,
        ):
            query.has_vocal = False
        else:
            concepts = ontology.extract_concepts(chunk)
            query.negated_genres.extend(concepts["genres"])
            query.negated_moods.extend(concepts["moods"])
    positive_text = "".join(masked_chars)

    # 2. Положительные сущности.
    concepts = ontology.extract_concepts(positive_text)
    query.genres = concepts["genres"]
    query.moods = concepts["moods"]
    query.negated_genres = sorted(set(query.negated_genres))
    query.negated_moods = sorted(set(query.negated_moods))

    # 3. Вокал: отрицание уже обработано, здесь только положительные формы.
    if query.has_vocal is None:
        if _NO_INSTRUMENTAL_RE.search(positive_text):
            query.has_vocal = True
        elif _NO_VOCALS_RE.search(positive_text):
            query.has_vocal = False
        elif _INSTRUMENTAL_RE.search(positive_text):
            query.has_vocal = False
        elif _VOCAL_RE.search(positive_text):
            query.has_vocal = True

    # 4. Годы и десятилетия. Длинная форма важнее обычного года:
    # «2010-е» — это диапазон, а не 2010 год.
    long_decade = _LONG_DECADE_RE.search(positive_text)
    years = [int(value) for value in _YEAR_RE.findall(positive_text)]
    if long_decade:
        start = int(long_decade.group(1))
        query.year_from = start
        query.year_to = start + 9
    elif years:
        query.year_from = min(years)
        query.year_to = max(years)
    else:
        decade = _DECADE_RE.search(positive_text)
        if decade:
            value = int(decade.group(1))
            start = 1900 + value if value >= 30 else 2000 + value
            query.year_from = start
            query.year_to = start + 9
        else:
            lowered = positive_text.lower()
            for word, start in _WORD_DECADES.items():
                if re.search(rf"(?<!\w){word}(?!\w)", lowered):
                    query.year_from = start
                    query.year_to = start + 9
                    break

    # 5. Исполнитель: кавычки имеют приоритет над конструкцией «artist ...».
    quoted = _QUOTED_RE.search(raw)
    if quoted:
        query.artist = quoted.group(1).strip()
    else:
        artist = _ARTIST_RE.search(positive_text)
        if artist:
            candidate = artist.group(1).strip()
            candidate = re.split(r"\b(?:жанр|настроение|год|genre|mood)\b", candidate, maxsplit=1, flags=re.IGNORECASE)[0]
            query.artist = candidate.strip(" ,-")

    # 6. Семантический текст для CLAP: канонические английские промпты.
    semantic_parts: list[str] = []
    for genre in query.genres:
        semantic_parts.append(ontology.get_genre_prompt(genre))
    for mood in query.moods:
        semantic_parts.append(ontology.get_mood_prompt(mood))
    for genre in query.negated_genres:
        semantic_parts.append("not " + ontology.get_genre_prompt(genre))
    for mood in query.negated_moods:
        semantic_parts.append("not " + ontology.get_mood_prompt(mood))
    if query.has_vocal is True:
        semantic_parts.append("with vocals")
    elif query.has_vocal is False:
        semantic_parts.append("instrumental, no vocals")
    if not semantic_parts:
        semantic_parts.append(raw)
    else:
        # Свободный текст тоже может быть полезен, но не дублируем его,
        # если он состоит только из распознанных понятий.
        free = positive_text.strip(" ,.-")
        if free and not ontology.extract_concepts(free)["genres"] and not ontology.extract_concepts(free)["moods"]:
            semantic_parts.append(free)
    query.semantic_text = ", ".join(part for part in semantic_parts if part).strip()

    # 7. Свободный текст для лексического канала.
    query.free_text = re.sub(r"\s+", " ", positive_text).strip(" ,.-")
    return query


def is_negative_only(query: ParsedQuery) -> bool:
    return bool(query.negated_genres or query.negated_moods) and not (
        query.genres or query.moods or query.free_text
    )
