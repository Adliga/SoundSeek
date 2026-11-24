# """Форматирование данных для Gradio-интерфейса."""

# from __future__ import annotations

# from html import escape
# from pathlib import Path

# from soundseek_core.models import ParsedQuery, SearchHit, Track
# from web_app.player_ui import play_button_html

# STATUS_LABELS = {
#     "idle": ("Распознать текст", "secondary"),
#     "queued": ("В очереди", "secondary"),
#     "running": ("Распознавание...", "primary"),
#     "done": ("Готово", "secondary"),
#     "error": ("Ошибка — повторить", "stop"),
#     "has_lyrics": ("Текст уже есть", "secondary"),
#     "skipped": ("Не требуется", "secondary"),
# }


# def vocal_label(track: Track) -> str:
#     if track.derived.has_vocal is True:
#         return "да"
#     if track.derived.has_vocal is False:
#         return "нет"
#     return "не проверено"


# def status_label(status: str) -> tuple[str, str]:
#     return STATUS_LABELS.get(status, ("Распознать текст", "secondary"))


# def track_choice_label(track: Track) -> str:
#     artist = f" — {track.tags.artist}" if track.tags.artist else ""
#     return f"{track.display_title}{artist}"


# def track_choices(tracks: list[Track]) -> list[tuple[str, str]]:
#     return [(track_choice_label(track), track.id) for track in tracks]


# def _channel_summary(hit: SearchHit) -> str:
#     parts = []
#     if "metadata" in hit.channels:
#         parts.append("метаданные")
#     if "clap" in hit.channels:
#         parts.append(f"CLAP {hit.channels['clap']:.3f}")
#     if "lyrics" in hit.channels:
#         parts.append(f"текст {hit.channels['lyrics']:.3f}")
#     if "notes" in hit.channels:
#         parts.append(f"заметки {hit.channels['notes']:.3f}")
#     if "audio" in hit.channels:
#         parts.append(f"аудио {hit.channels['audio']:.3f}")
#     if "melody" in hit.channels:
#         parts.append(f"мелодия {hit.channels['melody']:.3f}")
#     if "filter" in hit.channels:
#         parts.append("фильтр")
#     return " · ".join(parts) if parts else "—"


# def format_results(
#     results: list[SearchHit],
#     query_summary: str = "",
#     empty_hint: str = "",
#     summary_title: str = "Разбор запроса",
# ) -> str:
#     summary = (
#         f"<p class='soundseek-summary' style='font-size:13px;margin-bottom:10px;'>"
#         f"{escape(summary_title)}: {escape(query_summary)}</p>"
#         if query_summary
#         else ""
#     )
#     if not results:
#         hint = empty_hint.strip() or (
#             "Ничего не найдено. Попробуйте убрать отрицание, изменить жанр "
#             "или сформулировать описание звучания."
#         )
#         return summary + (
#             "<div class='soundseek-warning-card' style='padding:16px;"
#             "border:1px solid #e0c9a6;border-radius:8px;'>"
#             f"{escape(hint)}</div>"
#         )

#     blocks = []
#     for index, hit in enumerate(results, 1):
#         track = hit.track
#         title = escape(track.display_title)
#         artist = escape(track.tags.artist or "—")
#         album = escape(track.tags.album or "—")
#         explanations = "".join(
#             f"<li>{escape(explanation)}</li>"
#             for explanation in hit.explanations
#             if explanation
#         )
#         lyrics = ""
#         if track.derived.lyrics:
#             full_lyrics = track.derived.lyrics.strip().replace("\n", " ")
#             snippet = escape(full_lyrics[:220])
#             if len(full_lyrics) > 220:
#                 snippet += "…"
#             lyrics = (
#                 "<div class='soundseek-muted' style='font-size:12px;margin-top:6px;'>"
#                 f"<b>Текст:</b> {snippet}</div>"
#             )
#         notes = ""
#         if track.derived.user_notes:
#             note_text = track.derived.user_notes.strip().replace("\n", " ")
#             snippet = escape(note_text[:180])
#             if len(note_text) > 180:
#                 snippet += "…"
#             notes = (
#                 "<div class='soundseek-muted' style='font-size:12px;margin-top:6px;'>"
#                 f"<b>Заметка:</b> {snippet}</div>"
#             )
#         source = escape(track.derived.genre_source or "—")
#         blocks.append(
#             f"""
#             <div class="soundseek-light-card" style="border:1px solid #d0d7e2;border-radius:10px;padding:14px;
#                         margin-bottom:12px;background:#ffffff;color:#1a2b47;">
#               <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;">
#                 <div style="font-size:16px;font-weight:650;min-width:0;">{index}. {title}</div>
#                 {play_button_html(track.id, track.display_title)}
#               </div>
#               <div class="soundseek-muted" style="font-size:13px;margin:3px 0;">
#                 {artist} · {album}
#               </div>
#               <div class="soundseek-muted" style="font-size:13px;margin:6px 0;">
#                 Тип: <b>{escape(track.derived.content_type or "—")}</b> ·
#                 Жанр: <b>{escape(track.derived.genre or "—")}</b>
#                 <span class="soundseek-faint">({source})</span> ·
#                 Настроение: <b>{escape(track.derived.mood or "—")}</b> ·
#                 Вокал: <b>{vocal_label(track)}</b>
#               </div>
#               <div style="font-size:13px;margin:6px 0;">
#                 Оценка: <b>{hit.final_score:.3f}</b>
#                 <span class="soundseek-faint">(база {hit.base_score:.3f}; {escape(_channel_summary(hit))})</span>
#               </div>
#               <div style="font-size:13px;margin-top:8px;">
#                 <b>Почему найден:</b>
#                 <ul style="margin:4px 0 0 20px;">{explanations}</ul>
#               </div>
#               {lyrics}
#               {notes}
#             </div>
#             """
#         )
#     return summary + "<div>" + "".join(blocks) + "</div>"


# def format_query_summary(parsed: ParsedQuery) -> str:
#     return parsed.describe()


# def cover_path(track: Track | None) -> str | None:
#     if track is None:
#         return None
#     path = Path(track.tags.cover_path) if track.tags.cover_path else None
#     return str(path) if path and path.exists() else None



"""Форматирование данных для Gradio-интерфейса."""

from __future__ import annotations

from html import escape
from pathlib import Path

from soundseek_core.models import ParsedQuery, SearchHit, Track
from web_app.player_ui import play_button_html

STATUS_LABELS = {
    "idle": ("Распознать текст", "secondary"),
    "queued": ("В очереди", "secondary"),
    "running": ("Распознавание...", "primary"),
    "done": ("Готово", "secondary"),
    "error": ("Ошибка — повторить", "stop"),
    "has_lyrics": ("Текст уже есть", "secondary"),
    "skipped": ("Не требуется", "secondary"),
}


def vocal_label(track: Track) -> str:
    if track.derived.has_vocal is True:
        return "да"
    if track.derived.has_vocal is False:
        return "нет"
    return "не проверено"


def status_label(status: str) -> tuple[str, str]:
    return STATUS_LABELS.get(status, ("Распознать текст", "secondary"))


def track_choice_label(track: Track) -> str:
    artist = f" — {track.tags.artist}" if track.tags.artist else ""
    return f"{track.display_title}{artist}"


def track_choices(tracks: list[Track]) -> list[tuple[str, str]]:
    return [(track_choice_label(track), track.id) for track in tracks]


def _channel_summary(hit: SearchHit) -> str:
    parts = []
    if "metadata" in hit.channels:
        parts.append("метаданные")
    if "clap" in hit.channels:
        parts.append(f"CLAP {hit.channels['clap']:.3f}")
    if "lyrics" in hit.channels:
        parts.append(f"текст {hit.channels['lyrics']:.3f}")
    if "notes" in hit.channels:
        parts.append(f"заметки {hit.channels['notes']:.3f}")
    if "audio" in hit.channels:
        parts.append(f"аудио {hit.channels['audio']:.3f}")
    if "melody" in hit.channels:
        parts.append(f"мелодия {hit.channels['melody']:.3f}")
    if "filter" in hit.channels:
        parts.append("фильтр")
    return " · ".join(parts) if parts else "—"


def _result_chips(track: Track) -> str:
    source = escape(track.derived.genre_source or "—")
    chips = [
        f'<span class="soundseek-chip">Тип: '
        f'<b>{escape(track.derived.content_type or "—")}</b></span>',
        f'<span class="soundseek-chip">Жанр: '
        f'<b>{escape(track.derived.genre or "—")}</b> '
        f'<span class="soundseek-chip-source">({source})</span></span>',
        f'<span class="soundseek-chip">Настроение: '
        f'<b>{escape(track.derived.mood or "—")}</b></span>',
        f'<span class="soundseek-chip">Вокал: '
        f'<b>{vocal_label(track)}</b></span>',
    ]
    return "".join(chips)


def format_results(
    results: list[SearchHit],
    query_summary: str = "",
    empty_hint: str = "",
    summary_title: str = "Разбор запроса",
) -> str:
    summary = ""
    if query_summary:
        summary = (
            '<div class="soundseek-summary">'
            f'<span class="soundseek-summary-label">'
            f'{escape(summary_title)}</span>'
            f'<span class="soundseek-summary-text">'
            f'{escape(query_summary)}</span>'
            '</div>'
        )

    if not results:
        hint = empty_hint.strip() or (
            "Ничего не найдено. Попробуйте убрать отрицание, изменить жанр "
            "или сформулировать описание звучания."
        )
        return summary + (
            '<div class="soundseek-empty-card">'
            '<span class="soundseek-empty-icon">∅</span>'
            f'<span class="soundseek-empty-text">{escape(hint)}</span>'
            '</div>'
        )

    blocks = []
    for index, hit in enumerate(results, 1):
        track = hit.track
        title = escape(track.display_title)
        artist = escape(track.tags.artist or "—")
        album = escape(track.tags.album or "—")

        explanations = "".join(
            f"<li>{escape(explanation)}</li>"
            for explanation in hit.explanations
            if explanation
        )

        lyrics_html = ""
        if track.derived.lyrics:
            full_lyrics = track.derived.lyrics.strip().replace("\n", " ")
            snippet = escape(full_lyrics[:220])
            if len(full_lyrics) > 220:
                snippet += "…"
            lyrics_html = (
                '<div class="soundseek-result-extra">'
                '<span class="soundseek-result-extra-label">Текст</span>'
                f'<span class="soundseek-result-extra-text">{snippet}</span>'
                '</div>'
            )

        notes_html = ""
        if track.derived.user_notes:
            note_text = track.derived.user_notes.strip().replace("\n", " ")
            snippet = escape(note_text[:180])
            if len(note_text) > 180:
                snippet += "…"
            notes_html = (
                '<div class="soundseek-result-extra">'
                '<span class="soundseek-result-extra-label">Заметка</span>'
                f'<span class="soundseek-result-extra-text">{snippet}</span>'
                '</div>'
            )

        channels = escape(_channel_summary(hit))
        chips = _result_chips(track)

        blocks.append(
            '<article class="soundseek-result-card">'
            '<header class="soundseek-result-head">'
            '<div class="soundseek-result-title">'
            f'<span class="soundseek-result-index">{index:02d}</span>'
            f'<span class="soundseek-result-name">{title}</span>'
            '</div>'
            f'{play_button_html(track.id, track.display_title)}'
            '</header>'
            f'<div class="soundseek-result-meta">{artist} · {album}</div>'
            f'<div class="soundseek-result-chips">{chips}</div>'
            '<div class="soundseek-result-score">'
            f'<span class="soundseek-score-value">{hit.final_score:.3f}</span>'
            f'<span class="soundseek-score-detail">'
            f'база {hit.base_score:.3f} · {channels}</span>'
            '</div>'
            '<div class="soundseek-result-why">'
            '<span class="soundseek-result-why-label">Почему найден</span>'
            f'<ul>{explanations}</ul>'
            '</div>'
            f'{lyrics_html}{notes_html}'
            '</article>'
        )

    return summary + '<div class="soundseek-results">' + "".join(blocks) + "</div>"


def format_query_summary(parsed: ParsedQuery) -> str:
    return parsed.describe()


def cover_path(track: Track | None) -> str | None:
    if track is None:
        return None
    path = Path(track.tags.cover_path) if track.tags.cover_path else None
    return str(path) if path and path.exists() else None

# ---------- HTML-таблица библиотеки ----------

def _format_duration(seconds: float) -> str:
    if not seconds or seconds <= 0:
        return "—"
    total = int(round(seconds))
    if total < 60:
        return f"{total} с"
    return f"{total // 60}:{total % 60:02d}"


def _status_cell(track: Track, status: str) -> str:
    """Пилюля «вокал» + кнопка/плашка распознавания в одной ячейке."""
    label, _ = status_label(status)
    vocal = vocal_label(track)

    vocal_class = "soundseek-lib-vocal"
    if vocal == "да":
        vocal_class += " is-yes"
    elif vocal == "нет":
        vocal_class += " is-no"
    vocal_chip = f'<span class="{vocal_class}">{escape(vocal)}</span>'

    # Кликабельные статусы: idle / error / skipped
    if status in ("idle", "error", "skipped"):
        force = "1" if status in ("error", "skipped") else "0"
        state = "error" if status == "error" else "idle"
        return (
            '<div class="soundseek-lib-status">'
            f'{vocal_chip}'
            f'<button type="button" class="soundseek-lib-enrich" '
            f'data-track-enrich="{escape(track.id, quote=True)}" '
            f'data-track-force="{force}" data-state="{state}">'
            f'{escape(label)}</button>'
            '</div>'
        )

    # Некликабельные: queued / running / done / has_lyrics
    chip_class = "soundseek-lib-status-chip"
    if status == "running":
        chip_class += " is-active"
    elif status in ("done", "has_lyrics"):
        chip_class += " is-done"
    return (
        f'<div class="soundseek-lib-status">{vocal_chip}'
        f'<span class="{chip_class}">{escape(label)}</span></div>'
    )


def format_library_table(
    tracks: list[Track],
    status_map: dict[str, str],
    selected_id: str = "",
) -> str:
    """Возвращает всю таблицу библиотеки одним HTML-блоком."""
    if not tracks:
        return (
            '<div class="soundseek-lib-empty">'
            "Нет треков, подходящих под фильтр."
            "</div>"
        )

    header = (
        '<div class="soundseek-lib-head">'
        '<div class="soundseek-lib-cell soundseek-lib-play"></div>'
        '<div class="soundseek-lib-cell soundseek-lib-index">#</div>'
        '<div class="soundseek-lib-cell">Название</div>'
        '<div class="soundseek-lib-cell">Тип</div>'
        '<div class="soundseek-lib-cell">Жанр</div>'
        '<div class="soundseek-lib-cell">Настроение</div>'
        '<div class="soundseek-lib-cell">Вокал / статус</div>'
        '<div class="soundseek-lib-cell soundseek-lib-duration">Время</div>'
        '</div>'
    )

    rows = []
    for index, track in enumerate(tracks, 1):
        status = status_map.get(
            track.id,
            "has_lyrics" if track.derived.lyrics else "idle",
        )
        title = escape(track.display_title)
        title_attr = escape(track.display_title, quote=True)
        content_type = escape(track.derived.content_type or "—")
        genre = escape(track.derived.genre or "—")
        mood = escape(track.derived.mood or "—")
        duration = _format_duration(track.derived.duration)

        selected_class = " is-selected" if track.id == selected_id else ""
        rows.append(
            f'<div class="soundseek-lib-row{selected_class}" data-track-id="'
            f'{escape(track.id, quote=True)}" tabindex="0" role="button">'
            f'<div class="soundseek-lib-cell soundseek-lib-play">'
            f'{play_button_html(track.id, track.display_title)}</div>'
            f'<div class="soundseek-lib-cell soundseek-lib-index">'
            f'{index:02d}</div>'
            f'<div class="soundseek-lib-cell">'
            f'<div class="soundseek-lib-title" title="{title_attr}">'
            f'{title}</div></div>'
            f'<div class="soundseek-lib-cell">'
            f'<span class="soundseek-lib-tag">{content_type}</span></div>'
            f'<div class="soundseek-lib-cell soundseek-lib-muted">{genre}</div>'
            f'<div class="soundseek-lib-cell soundseek-lib-muted">{mood}</div>'
            f'<div class="soundseek-lib-cell">{_status_cell(track, status)}</div>'
            f'<div class="soundseek-lib-cell soundseek-lib-duration">'
            f'{duration}</div>'
            '</div>'
        )

    return (
        '<div class="soundseek-lib">'
        '<div class="soundseek-lib-scroll">'
        f'{header}'
        f'{"".join(rows)}'
        '</div>'
        '</div>'
    )