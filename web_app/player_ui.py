"""Общие элементы глобального аудиоплеера.

Кнопки воспроизведения в HTML-списках используют делегирование событий:
клик по элементу ``[data-track-play]`` отправляет в Python событие
``track_play`` с идентификатором трека. Один и тот же обработчик обновляет
закреплённый плеер, поэтому списки не создают собственные аудиоплееры.
"""

from __future__ import annotations

from html import escape

from soundseek_core.models import Track

PLAY_BUTTON_JS = r"""
(() => {
  const root = element;
  if (!root || root.dataset.soundseekPlayBound === "1") return;
  root.dataset.soundseekPlayBound = "1";

  root.addEventListener("click", (event) => {
    const button = event.target.closest("[data-track-play]");
    if (!button || !root.contains(button)) return;
    event.preventDefault();
    event.stopPropagation();

    const trackId = button.dataset.trackPlay || "";
    if (!trackId) return;
    trigger("track_play", { track_id: trackId });
  });
})();
"""


def play_button_html(track_id: str, title: str = "") -> str:
    """Возвращает кнопку, которая включает трек в глобальном плеере."""
    track_id = (track_id or "").strip()
    if not track_id:
        return ""
    label = f"Воспроизвести {title}" if title else "Воспроизвести трек"
    return (
        '<button type="button" class="soundseek-play-button" '
        f'data-track-play="{escape(track_id, quote=True)}" '
        f'aria-label="{escape(label, quote=True)}" '
        'title="Воспроизвести">'
        '<span aria-hidden="true">▶</span>'
        "</button>"
    )


def format_player_meta(track: Track) -> str:
    """Краткая подпись текущего трека в закреплённом плеере."""
    title = escape(track.display_title or "Без названия")
    details = [escape(track.tags.artist or "—")]
    if track.tags.album:
        details.append(escape(track.tags.album))
    if track.derived.genre:
        details.append(escape(track.derived.genre))
    if track.derived.mood:
        details.append(escape(track.derived.mood))
    return (
        f'<div class="soundseek-player-track">{title}</div>'
        f'<div class="soundseek-player-artist">{" · ".join(details)}</div>'
    )


def format_player_error(message: str) -> str:
    return (
        '<div class="soundseek-player-error">'
        f"{escape(message)}</div>"
    )
