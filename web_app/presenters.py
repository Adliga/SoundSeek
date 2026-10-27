"""Форматирование данных для Gradio-интерфейса."""

from __future__ import annotations

from html import escape
from pathlib import Path

from soundseek_core.models import ParsedQuery, SearchHit, Track

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
    if "audio" in hit.channels:
        parts.append(f"аудио {hit.channels['audio']:.3f}")
    if "melody" in hit.channels:
        parts.append(f"мелодия {hit.channels['melody']:.3f}")
    if "filter" in hit.channels:
        parts.append("фильтр")
    return " · ".join(parts) if parts else "—"


def format_results(
    results: list[SearchHit],
    query_summary: str = "",
    empty_hint: str = "",
    summary_title: str = "Разбор запроса",
) -> str:
    summary = (
        f"<p style='color:#40506a;font-size:13px;margin-bottom:10px;'>"
        f"{escape(summary_title)}: {escape(query_summary)}</p>"
        if query_summary
        else ""
    )
    if not results:
        hint = empty_hint.strip() or (
            "Ничего не найдено. Попробуйте убрать отрицание, изменить жанр "
            "или сформулировать описание звучания."
        )
        return summary + (
            "<div style='padding:16px;border:1px solid #e0c9a6;"
            "border-radius:8px;background:#fff8e8;color:#5b4300;'>"
            f"{escape(hint)}</div>"
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
        lyrics = ""
        if track.derived.lyrics:
            full_lyrics = track.derived.lyrics.strip().replace("\n", " ")
            snippet = escape(full_lyrics[:220])
            if len(full_lyrics) > 220:
                snippet += "…"
            lyrics = (
                "<div style='font-size:12px;color:#4d5b70;margin-top:6px;'>"
                f"<b>Текст:</b> {snippet}</div>"
            )
        source = escape(track.derived.genre_source or "—")
        blocks.append(
            f"""
            <div style="border:1px solid #d0d7e2;border-radius:10px;padding:14px;
                        margin-bottom:12px;background:#ffffff;color:#1a2b47;">
              <div style="font-size:16px;font-weight:650;">{index}. {title}</div>
              <div style="color:#4d5b70;font-size:13px;margin:3px 0;">
                {artist} · {album}
              </div>
              <div style="color:#40506a;font-size:13px;margin:6px 0;">
                Тип: <b>{escape(track.derived.content_type or "—")}</b> ·
                Жанр: <b>{escape(track.derived.genre or "—")}</b>
                <span style="color:#8090a8;">({source})</span> ·
                Настроение: <b>{escape(track.derived.mood or "—")}</b> ·
                Вокал: <b>{vocal_label(track)}</b>
              </div>
              <div style="font-size:13px;margin:6px 0;">
                Оценка: <b>{hit.final_score:.3f}</b>
                <span style="color:#8090a8;">(база {hit.base_score:.3f}; {escape(_channel_summary(hit))})</span>
              </div>
              <div style="font-size:13px;margin-top:8px;">
                <b>Почему найден:</b>
                <ul style="margin:4px 0 0 20px;">{explanations}</ul>
              </div>
              {lyrics}
            </div>
            """
        )
    return summary + "<div>" + "".join(blocks) + "</div>"


def format_query_summary(parsed: ParsedQuery) -> str:
    return parsed.describe()


def cover_path(track: Track | None) -> str | None:
    if track is None:
        return None
    path = Path(track.tags.cover_path) if track.tags.cover_path else None
    return str(path) if path and path.exists() else None
