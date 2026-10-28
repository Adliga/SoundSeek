"""Визуализация аудиотеки в двумерном пространстве CLAP-эмбеддингов.

Используется PCA из scikit-learn и чистый SVG: это не требует plotly,
matplotlib или отдельного сервера и остаётся локальным. Легенда вынесена
из SVG в отдельный блок, поэтому подписи цветов не перекрывают точки.
"""

from __future__ import annotations

from collections import Counter
from html import escape

import numpy as np
from sklearn.decomposition import PCA

from .db import VectorDB

PALETTE = [
    "#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed", "#0891b2",
    "#be185d", "#65a30d", "#b45309", "#4338ca", "#0f766e", "#a21caf",
    "#e11d48", "#0284c7", "#ca8a04", "#4f46e5", "#15803d", "#c2410c",
    "#7e22ce", "#0e7490",
]

COLOR_LABELS = {
    "genre": "жанр",
    "mood": "настроение",
    "content_type": "тип контента",
}

MISSING_VALUE = "—"


def _color_map(values: list[str]) -> dict[str, str]:
    unique = sorted({value or MISSING_VALUE for value in values})
    return {value: PALETTE[i % len(PALETTE)] for i, value in enumerate(unique)}


def _shorten(text: str, limit: int = 42) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _display_value(value: str) -> str:
    return "не указано" if value in ("", MISSING_VALUE) else value


def _grid_lines(width: int, height: int) -> str:
    lines = []
    for fraction in (0.2, 0.4, 0.6, 0.8):
        x = width * fraction
        y = height * fraction
        lines.append(
            f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{height}" />'
        )
        lines.append(
            f'<line x1="0" y1="{y:.1f}" x2="{width}" y2="{y:.1f}" />'
        )
    return (
        '<g class="soundseek-map-grid" stroke="#e2e8f0" stroke-width="1" '
        'opacity="0.75">' + "".join(lines) + "</g>"
    )


def build_embedding_map(db: VectorDB, color_by: str = "genre") -> str:
    tracks = db.snapshot()
    matrix = db.audio_matrix()
    if len(tracks) < 2 or matrix.shape[0] != len(tracks):
        return (
            '<div class="soundseek-map-card soundseek-map-empty">'
            "<p><i>Недостаточно треков для визуализации.</i></p>"
            "</div>"
        )

    coords = PCA(n_components=2, random_state=42).fit_transform(matrix)
    minimum = coords.min(axis=0)
    maximum = coords.max(axis=0)
    span = np.where((maximum - minimum) < 1e-9, 1.0, maximum - minimum)
    normalized = (coords - minimum) / span

    if color_by == "mood":
        values = [track.derived.mood or MISSING_VALUE for track in tracks]
    elif color_by == "content_type":
        values = [
            track.derived.content_type or MISSING_VALUE for track in tracks
        ]
    else:
        values = [track.derived.genre or MISSING_VALUE for track in tracks]
    colors = _color_map(values)
    counts = Counter(values)

    width, height, margin = 900, 500, 44
    points = []
    for track, (x, y), value in zip(tracks, normalized, values):
        px = margin + float(x) * (width - 2 * margin)
        py = height - margin - float(y) * (height - 2 * margin)
        title = track.display_title or "Без названия"
        artist = track.tags.artist or MISSING_VALUE
        aria = _shorten(f"{title} — {artist}", limit=90)
        points.append(
            f'<g class="soundseek-map-point" '
            f'data-track-id="{escape(track.id, quote=True)}" '
            f'data-title="{escape(title, quote=True)}" '
            f'data-artist="{escape(artist, quote=True)}" '
            f'tabindex="0" role="button" '
            f'aria-label="{escape(aria, quote=True)}">'
            f'<circle class="soundseek-map-hit" cx="{px:.1f}" '
            f'cy="{py:.1f}" r="14" />'
            f'<circle class="soundseek-map-halo" cx="{px:.1f}" '
            f'cy="{py:.1f}" r="11" />'
            f'<circle class="soundseek-map-dot" cx="{px:.1f}" '
            f'cy="{py:.1f}" r="6.5" fill="{colors[value]}" />'
            "</g>"
        )

    legend_items = []
    for value, color in sorted(colors.items()):
        legend_items.append(
            '<span class="soundseek-map-legend-item">'
            f'<span class="soundseek-map-swatch" '
            f'style="background:{color}"></span>'
            f"<span>{escape(_display_value(value))}</span>"
            f'<span class="soundseek-map-legend-count">{counts[value]}</span>'
            "</span>"
        )

    color_label = COLOR_LABELS.get(color_by, "жанр")
    return (
        '<div class="soundseek-map-card">'
        '<div class="soundseek-map-head">'
        "<div>"
        '<div class="soundseek-map-kicker">CLAP · PCA · 2D</div>'
        '<div class="soundseek-map-title">Карта аудиотеки</div>'
        '<div class="soundseek-map-subtitle">'
        "Наведите на точку, чтобы увидеть трек. Нажмите — чтобы включить."
        "</div>"
        "</div>"
        f'<div class="soundseek-map-count">{len(tracks)} треков</div>'
        "</div>"
        '<div class="soundseek-map-canvas">'
        f'<svg class="soundseek-map-svg" viewBox="0 0 {width} {height}" '
        'role="group" aria-label="Карта CLAP-эмбеддингов">'
        + _grid_lines(width, height)
        + "".join(points)
        + "</svg>"
        "</div>"
        '<div class="soundseek-map-legend-block">'
        f'<div class="soundseek-map-legend-title">Цвет — {color_label}</div>'
        '<div class="soundseek-map-legend">'
        + "".join(legend_items)
        + "</div>"
        "</div>"
        "</div>"
    )
