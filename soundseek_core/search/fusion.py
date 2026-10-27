"""Слияние оценок независимых каналов.

Используется взвешенная нормированная сумма + RRF как tie-breaker.
Это проще объяснить на защите, чем «сырые» косинусы, которые имели
разный масштаб (метаданные 1.0, CLAP 0.2, правила ±0.3).
"""

from __future__ import annotations

from ..config import RRF_K
from ..models import Track

CHANNEL_WEIGHTS = {
    "metadata": 1.0,
    "clap": 0.8,
    "lyrics": 0.7,
    "audio": 1.0,
    "melody": 0.8,
    # Фильтр — источник кандидатов, а не сильный сигнал релевантности:
    # иначе все треки после жанрового правила получают одинаковые 1.0.
    "filter": 0.4,
}
DENOMINATOR = 1.6
MIN_FUSED_SCORE = 0.05


def calibrate(channel: str, raw_score: float) -> float:
    if channel in ("clap", "audio", "melody"):
        # Косинус CLAP на практике лежит в диапазоне ~0.1–0.7.
        return max(0.0, min(1.0, (raw_score - 0.10) / 0.90))
    return max(0.0, min(1.0, raw_score))


def fuse(channels: dict[str, list[tuple[Track, float]]]) -> list[tuple]:
    """Возвращает [(track, base_score, raw_channels, ranks), ...]."""
    merged: dict[str, dict] = {}
    for channel, results in channels.items():
        weight = CHANNEL_WEIGHTS.get(channel, 0.5)
        for rank, (track, raw_score) in enumerate(results):
            item = merged.setdefault(
                track.id,
                {
                    "track": track,
                    "score": 0.0,
                    "rrf": 0.0,
                    "raw": {},
                    "ranks": {},
                },
            )
            item["score"] += weight * calibrate(channel, float(raw_score))
            item["rrf"] += weight / (RRF_K + rank)
            item["raw"][channel] = round(float(raw_score), 4)
            item["ranks"][channel] = rank + 1

    fused = []
    for item in merged.values():
        base = min(1.0, item["score"] / DENOMINATOR)
        if base < MIN_FUSED_SCORE:
            continue
        fused.append(
            (
                item["track"],
                round(base, 4),
                item["raw"],
                item["ranks"],
                item["rrf"],
            )
        )
    fused.sort(
        key=lambda entry: (
            -entry[1],
            -entry[4],
            entry[0].display_title.lower(),
        )
    )
    # RRF уже использован для сортировки. Возвращаем четвёрку, чтобы
    # правило могло получить ранги, но не зависело от пятого поля.
    return [(track, base, raw, ranks) for track, base, raw, ranks, _ in fused]
