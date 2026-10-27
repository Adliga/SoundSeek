"""Визуализация аудиотеки в двумерном пространстве CLAP-эмбеддингов.

Используется PCA из scikit-learn и чистый SVG: это не требует plotly,
matplotlib или отдельного сервера и остаётся локальным.
"""

from __future__ import annotations

from html import escape

import numpy as np
from sklearn.decomposition import PCA

from .db import VectorDB

PALETTE = [
    "#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed", "#0891b2",
    "#be185d", "#4d7c0f", "#b45309", "#4338ca", "#0f766e", "#a21caf",
]


def _color_map(values: list[str]) -> dict[str, str]:
    unique = sorted({value or "—" for value in values})
    return {value: PALETTE[i % len(PALETTE)] for i, value in enumerate(unique)}


def build_embedding_map(db: VectorDB, color_by: str = "genre") -> str:
    tracks = db.snapshot()
    matrix = db.audio_matrix()
    if len(tracks) < 2 or matrix.shape[0] != len(tracks):
        return "<p><i>Недостаточно треков для визуализации.</i></p>"

    coords = PCA(n_components=2, random_state=42).fit_transform(matrix)
    minimum = coords.min(axis=0)
    maximum = coords.max(axis=0)
    span = np.where((maximum - minimum) < 1e-9, 1.0, maximum - minimum)
    normalized = (coords - minimum) / span

    if color_by == "mood":
        values = [track.derived.mood or "—" for track in tracks]
    elif color_by == "content_type":
        values = [track.derived.content_type or "—" for track in tracks]
    else:
        values = [track.derived.genre or "—" for track in tracks]
    colors = _color_map(values)

    width, height, margin = 760, 440, 34
    points = []
    for track, (x, y), value in zip(tracks, normalized, values):
        px = margin + float(x) * (width - 2 * margin)
        py = height - margin - float(y) * (height - 2 * margin)
        title = escape(
            f"{track.display_title} | {track.tags.artist or '—'} | "
            f"{track.derived.genre or '—'} / {track.derived.mood or '—'}"
        )
        points.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" '
            f'fill="{colors[value]}" stroke="#ffffff" stroke-width="1.5" '
            f'opacity="0.9"><title>{title}</title></circle>'
        )

    legend = []
    for index, (value, color) in enumerate(sorted(colors.items())):
        column = index % 3
        row = index // 3
        lx = 18 + column * 245
        ly = 22 + row * 20
        legend.append(
            f'<rect x="{lx}" y="{ly - 9}" width="10" height="10" fill="{color}" rx="2"/>'
            f'<text x="{lx + 15}" y="{ly}" font-size="12" fill="#334155">'
            f"{escape(value)}</text>"
        )

    return (
        f'<svg viewBox="0 0 {width} {height + 30}" width="100%" '
        'style="background:#f8fafc;border:1px solid #dbe3ee;border-radius:10px;">'
        f'<text x="{width/2}" y="18" text-anchor="middle" font-size="14" '
        'font-weight="600" fill="#1e293b">Карта CLAP-эмбеддингов (PCA, 2D)</text>'
        + "".join(points)
        + "".join(legend)
        + "</svg>"
    )
