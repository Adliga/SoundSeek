"""Gradio-интерфейс SoundSeek.

Файл отвечает только за сборку интерфейса и связывание компонентов.
Форматирование вынесено в ``presenters``, фоновая очередь — в ``worker``.
"""

from __future__ import annotations

import shutil
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gradio as gr

from soundseek_core.albums import build_album_sections
from soundseek_core.config import (
    AUDIO_EMBEDDING_VERSION,
    INDEX_PATH,
    TRACKS_DIR,
    ensure_directories,
)
from soundseek_core.indexer import AudioIndexer
from soundseek_core.ontology import Ontology
from soundseek_core.playlist import generate_playlist
from soundseek_core.query_parser import parse_query
from soundseek_core.searcher import Searcher
from soundseek_core.visualization import build_embedding_map
from web_app.album_presenters import build_albums_view, format_album_detail
from web_app.albums_ui import ALBUM_JS
from web_app.map_ui import MAP_JS
from web_app.player_ui import (
    PLAY_BUTTON_JS,
    format_player_error,
    format_player_meta,
    play_button_html,
)
from web_app.presenters import (
    cover_path,
    format_results,
    status_label,
    track_choices,
    vocal_label,
)
from web_app.styles import APP_CSS
from web_app.worker import EnrichmentQueue

ensure_directories()

print("Инициализация SoundSeek...")
ontology = Ontology()
indexer = AudioIndexer(db_path=str(INDEX_PATH), ontology=ontology)
searcher = Searcher(indexer, ontology)
worker = EnrichmentQueue(indexer)
print("Готово.")

GENRE_CHOICES = [""] + ontology.genre_names
MOOD_CHOICES = [""] + ontology.mood_names
VOCAL_CHOICES = [
    ("все", ""),
    ("с вокалом", "yes"),
    ("без вокала", "no"),
    ("вокал не проверен", "unknown"),
]


def get_track_choices():
    return track_choices(indexer.db.snapshot())


def get_status_map():
    return worker.status_map()


def enqueue_and_status(track_id: str, force: bool = False):
    worker.enqueue(track_id, force=force)
    return worker.status_map()


def enqueue_all():
    for track in indexer.db.snapshot():
        status = track.derived.enrich_status
        if status in ("", "idle", "error", "skipped"):
            worker.enqueue(track.id, force=status in ("error", "skipped"))
    return worker.status_map()


# ---------- Библиотека ----------
def add_files_to_library(files, progress=gr.Progress()):
    if not files:
        return (
            "Файлы не выбраны.",
            gr.update(choices=get_track_choices(), value=None),
            worker.status_map(),
        )
    if worker.is_busy():
        return (
            "Сначала дождитесь завершения распознавания текста.",
            gr.update(choices=get_track_choices(), value=None),
            worker.status_map(),
        )

    copied = []
    skipped = []
    for item in files:
        source = Path(getattr(item, "name", item))
        destination = TRACKS_DIR / source.name
        if destination.exists():
            skipped.append(source.name)
            continue
        try:
            shutil.copy2(source, destination)
            copied.append(source.name)
        except Exception as exc:
            skipped.append(f"{source.name} ({exc})")

    stats = indexer.sync_folder(TRACKS_DIR, progress=progress)
    message = (
        f"Скопировано: {len(copied)}, пропущено: {len(skipped)}. "
        f"Индексация: {stats.summary()}."
    )
    if stats.errors:
        message += "\nОшибки: " + "; ".join(stats.errors[:3])
    return (
        message,
        gr.update(choices=get_track_choices(), value=None),
        worker.status_map(),
    )


def refresh_library(force: bool, progress=gr.Progress()):
    if worker.is_busy():
        return (
            "Сначала дождитесь завершения распознавания текста.",
            gr.update(choices=get_track_choices(), value=None),
            worker.status_map(),
        )
    if force:
        if not worker.reset():
            return (
                "Не удалось сбросить очередь распознавания.",
                gr.update(choices=get_track_choices(), value=None),
                worker.status_map(),
            )
        # Не сбрасываем базу: force-синхронизация перезапишет признаки,
        # но сохранит ручные правки, тексты и статусы обогащения.
    stats = indexer.sync_folder(TRACKS_DIR, force=force, progress=progress)
    prefix = "Переиндексировано" if force else "Обновлено"
    message = f"{prefix}: {stats.summary()}."
    if stats.errors:
        message += "\nОшибки: " + "; ".join(stats.errors[:3])
    return (
        message,
        gr.update(choices=get_track_choices(), value=None),
        worker.status_map(),
    )


def remove_track(track_id: str):
    if not track_id:
        return (
            "Трек не выбран.",
            gr.update(choices=get_track_choices(), value=None),
            worker.status_map(),
        )
    if worker.is_busy():
        return (
            "Сначала дождитесь завершения распознавания текста.",
            gr.update(choices=get_track_choices(), value=None),
            worker.status_map(),
        )
    removed = indexer.remove_track(track_id)
    message = "Трек удалён из индекса." if removed else "Трек не найден."
    return (
        message,
        gr.update(choices=get_track_choices(), value=None),
        worker.status_map(),
    )


# ---------- Карточка и редактирование ----------
def load_track_for_edit(track_id):
    empty = (None, "", "", "", "", "", "", "", "", "", "")
    if not track_id:
        return empty
    track = indexer.db.get(track_id)
    if not track:
        return empty
    year = str(track.tags.year) if track.tags.year else ""
    return (
        cover_path(track),
        track.tags.title,
        track.tags.artist,
        track.tags.album,
        year,
        track.tags.genre,
        track.derived.genre,
        track.derived.mood,
        track.derived.lyrics,
        track.derived.user_notes,
        track.id,
    )


def save_track_edits(
    track_id,
    title,
    artist,
    album,
    year_str,
    tag_genre,
    derived_genre,
    derived_mood,
    lyrics,
    user_notes,
):
    if not track_id:
        return "Не выбран трек.", worker.status_map()
    year = 0
    if year_str and str(year_str).strip():
        try:
            year = int(str(year_str).strip())
        except ValueError:
            return "Год должен быть числом, например 2019.", worker.status_map()
        if not 1000 <= year <= 3000:
            return "Год вне допустимого диапазона.", worker.status_map()
    track = indexer.update_track_fields(
        track_id,
        title=title,
        artist=artist,
        album=album,
        year=year,
        tag_genre=tag_genre,
        derived_genre=derived_genre,
        derived_mood=derived_mood,
        lyrics=lyrics,
        user_notes=user_notes,
    )
    if not track:
        return f"Трек {track_id} не найден.", worker.status_map()
    return f"Сохранено: {track.display_title}", worker.status_map()


def retry_enrichment(track_id):
    if not track_id:
        return "Не выбран трек.", worker.status_map()
    worker.enqueue(track_id, force=True)
    return "Задача поставлена в очередь.", worker.status_map()


# ---------- Поиск ----------
def handle_text_search(query: str, top_k: int):
    if not query.strip():
        return format_results([], "Введите запрос.")
    try:
        parsed = parse_query(query, ontology)
        results = searcher.search(query, top_k=int(top_k))
    except Exception as exc:
        return format_results([], f"Ошибка поиска: {exc}")
    hint = ""
    if not results and parsed.has_vocal is False:
        hint = (
            "Нет треков с подтверждённым отсутствием вокала. "
            "Запустите распознавание в библиотеке или снимите фильтр."
        )
    elif not results and (
        parsed.year_from is not None or parsed.year_to is not None
    ):
        hint = (
            "В метаданных нет треков с подходящим годом. "
            "Проверьте теги или укажите более широкий диапазон."
        )
    elif not results and parsed.moods:
        hint = (
            "Нет треков с подтверждённым подходящим настроением. "
            "Попробуйте другое настроение или исправьте его в карточке трека."
        )
    return format_results(results, parsed.describe(), hint)


def handle_audio_search(audio_path, top_k: int):
    if audio_path is None:
        return format_results([], empty_hint="Запишите или загрузите аудио.")
    try:
        results = searcher.search_by_audio(audio_path, top_k=int(top_k))
    except Exception as exc:
        return format_results(
            [],
            empty_hint=f"Не удалось прочитать аудиофрагмент: {exc}",
        )
    return format_results(
        results,
        "поиск по аудиофрагменту: CLAP-тембр + мелодический контур",
        summary_title="Режим",
    )


def update_embedding_map(color_by: str):
    return build_embedding_map(indexer.db, color_by=color_by)


def _player_audio(path: str | None) -> gr.Audio:
    return gr.Audio(
        value=path,
        visible=bool(path),
        autoplay=bool(path),
        interactive=False,
        show_label=False,
        buttons=[],
        type="filepath",
        elem_id="soundseek-global-audio",
    )


def play_track(track_id: str):
    """Включает трек в единственном закреплённом плеере."""
    track = indexer.db.get(str(track_id or ""))
    if track is None or not Path(track.path).is_file():
        message = (
            "Трек не найден."
            if track is None
            else "Файл трека недоступен."
        )
        return (
            gr.update(visible=True),
            _player_audio(None),
            format_player_error(message),
        )
    return (
        gr.update(visible=True),
        _player_audio(track.path),
        format_player_meta(track),
    )


def close_global_player():
    """Скрывает плеер и останавливает текущее воспроизведение."""
    return (
        gr.update(visible=False),
        _player_audio(None),
        "",
    )


def handle_track_play(evt: gr.EventData):
    return play_track(str(getattr(evt, "track_id", "") or ""))


def album_sections():
    return build_album_sections(indexer.db.snapshot())


def _find_album(key: str):
    type_albums, metadata_albums = album_sections()
    return next(
        (
            item
            for item in (*type_albums, *metadata_albums)
            if item.key == key
        ),
        None,
    )


def update_albums(selected_key: str):
    type_albums, metadata_albums = album_sections()
    return (
        build_albums_view(type_albums, metadata_albums),
        format_album_detail(_find_album(selected_key or "")),
    )


def handle_album_click(evt: gr.EventData):
    """Показывает треки выбранного альбома."""
    key = str(getattr(evt, "album_key", "") or "")
    return key, format_album_detail(_find_album(key))


def make_playlist(target_mood, start_mood, end_mood, length, genre):
    items = generate_playlist(
        indexer.db,
        ontology,
        target_mood=target_mood or "",
        start_mood=start_mood or "",
        end_mood=end_mood or "",
        length=int(length),
        genre=genre or "",
    )
    if not items:
        return "<p><i>Не удалось собрать плейлист: в библиотеке нет подходящих треков.</i></p>"
    rows = []
    for index, item in enumerate(items, 1):
        track = item.track
        rows.append(
            "<li style='display:flex;align-items:flex-start;gap:10px;margin:8px 0;'>"
            f"{play_button_html(track.id, track.display_title)}"
            "<div>"
            f"<b>{index}. {escape(track.display_title)}</b>"
            f" — {escape(track.tags.artist or '—')}<br>"
            f"<span class='soundseek-muted' style='font-size:12px;'>"
            f"{escape(track.derived.genre or '—')} / {escape(track.derived.mood or '—')} · "
            f"оценка {item.score:.3f} · {escape(item.reason)}</span>"
            "</div></li>"
        )
    return (
        "<div class='soundseek-light-card' style='border:1px solid #dbe3ee;"
        "border-radius:10px;padding:14px;color:#1a2b47;'>"
        "<ol style='margin:0 0 0 20px;'>"
        + "".join(rows)
        + "</ol></div>"
    )


# ---------- Интерфейс ----------
with gr.Blocks(
    title="SoundSeek",
) as demo:
    gr.Markdown(
        "# SoundSeek\n"
        "Локальная гибридная система поиска в аудиотеке: метаданные, "
        "CLAP, тексты песен и онтологические правила."
    )

    track_status_state = gr.State(get_status_map())

    with gr.Column(
        visible=False,
        elem_id="soundseek-global-player",
    ) as global_player:
        gr.Markdown(
            "### Сейчас играет",
            elem_classes="soundseek-global-title",
        )
        global_close = gr.Button(
            "✕",
            size="sm",
            variant="secondary",
            elem_id="soundseek-global-close",
        )
        global_meta = gr.HTML(
            "",
            elem_classes="soundseek-global-meta",
        )
        global_audio = gr.Audio(
            visible=False,
            autoplay=False,
            interactive=False,
            show_label=False,
            buttons=[],
            type="filepath",
            elem_id="soundseek-global-audio",
        )
    global_close.click(
        fn=close_global_player,
        inputs=None,
        outputs=[global_player, global_audio, global_meta],
    )

    with gr.Tabs():
        with gr.Tab("Поиск по тексту"):
            with gr.Row():
                text_input = gr.Textbox(
                    label="Что ищем?",
                    placeholder="например: грустный рок, lonely day, весёлый панк",
                    scale=4,
                )
                top_k_text = gr.Slider(
                    1, 20, value=5, step=1, label="Сколько показать", scale=1
                )
                text_btn = gr.Button("Найти", variant="primary", scale=1)
            text_output = gr.HTML(
                label="Результаты",
                js_on_load=PLAY_BUTTON_JS,
            )
            text_output.track_play(
                fn=handle_track_play,
                inputs=None,
                outputs=[global_player, global_audio, global_meta],
            )
            text_btn.click(
                handle_text_search,
                inputs=[text_input, top_k_text],
                outputs=text_output,
            )
            text_input.submit(
                handle_text_search,
                inputs=[text_input, top_k_text],
                outputs=text_output,
            )
            gr.Examples(
                examples=[
                    "lonely day",
                    "грустный рок",
                    "весёлый панк",
                    "рок, но не панк",
                    "trap",
                    "piano",
                ],
                inputs=text_input,
            )

        with gr.Tab("Поиск по аудио"):
            gr.Markdown(
                "Загрузите фрагмент трека или запишите напевание. "
                "Используются два сигнала: CLAP-эмбеддинг тембра и "
                "мелодический контур (pyin + DTW). Для напевания мелодия "
                "обычно важнее тембра."
            )
            audio_input = gr.Audio(
                sources=["microphone", "upload"],
                type="filepath",
                label="Аудиофрагмент",
            )
            top_k_audio = gr.Slider(
                1, 20, value=5, step=1, label="Сколько показать"
            )
            audio_btn = gr.Button("Найти похожее", variant="primary")
            audio_output = gr.HTML(
                label="Результаты",
                js_on_load=PLAY_BUTTON_JS,
            )
            audio_output.track_play(
                fn=handle_track_play,
                inputs=None,
                outputs=[global_player, global_audio, global_meta],
            )
            audio_btn.click(
                handle_audio_search,
                inputs=[audio_input, top_k_audio],
                outputs=audio_output,
            )

        with gr.Tab("Библиотека"):
            gr.Markdown("### Добавление треков")
            gr.Markdown(
                "Файлы копируются в `data/tracks/`, после чего выполняется "
                "инкрементальная синхронизация: новые и изменённые треки "
                "индексируются, удалённые исчезают из базы."
            )
            with gr.Row():
                upload_files = gr.File(
                    label="Выберите файлы",
                    file_count="multiple",
                    file_types=["audio"],
                    scale=4,
                )
                with gr.Column(scale=1):
                    add_btn = gr.Button("Добавить в библиотеку", variant="primary")
                    refresh_btn = gr.Button("Обновить библиотеку")
                    force_reindex = gr.Checkbox(
                        label="Переиндексировать всё",
                        value=False,
                        info="Пересчитывает признаки всех треков, сохраняя ручные правки",
                    )
                    enqueue_all_btn = gr.Button("Распознать текст у всех")
            status_msg = gr.Textbox(label="Статус", interactive=False)

            with gr.Row():
                library_filter = gr.Textbox(
                    label="Фильтр по названию/исполнителю",
                    placeholder="начните вводить...",
                    scale=2,
                )
                library_genre = gr.Dropdown(
                    choices=GENRE_CHOICES,
                    value="",
                    label="Жанр",
                    scale=1,
                )
                library_mood = gr.Dropdown(
                    choices=MOOD_CHOICES,
                    value="",
                    label="Настроение",
                    scale=1,
                )
                library_vocal = gr.Dropdown(
                    choices=VOCAL_CHOICES,
                    value="",
                    label="Вокал",
                    scale=1,
                )

            gr.Markdown(
                "Кнопка в колонке «Вокал» запускает Demucs + Whisper. "
                "Ошибки сохраняются и доступны для повторного запуска."
            )

            @gr.render(
                inputs=[
                    track_status_state,
                    library_filter,
                    library_genre,
                    library_mood,
                    library_vocal,
                ]
            )
            def render_tracks(
                status_map,
                filter_text,
                genre_filter,
                mood_filter,
                vocal_filter,
            ):
                tracks = indexer.db.snapshot()
                if not tracks:
                    gr.Markdown("_Пока нет треков. Добавьте файлы выше._")
                    return

                status_map = status_map or {}
                filter_text = (filter_text or "").lower().strip()
                visible = []
                for track in tracks:
                    haystack = " ".join(
                        [
                            track.display_title,
                            track.tags.artist,
                            track.tags.album,
                            track.tags.genre,
                            track.derived.genre,
                            track.derived.mood,
                            track.derived.user_notes,
                        ]
                    ).lower()
                    if filter_text and filter_text not in haystack:
                        continue
                    if genre_filter and track.derived.genre != genre_filter:
                        continue
                    if mood_filter and track.derived.mood != mood_filter:
                        continue
                    if vocal_filter == "yes" and track.derived.has_vocal is not True:
                        continue
                    if vocal_filter == "no" and track.derived.has_vocal is not False:
                        continue
                    if vocal_filter == "unknown" and track.derived.has_vocal is not None:
                        continue
                    visible.append(track)

                stale = sum(
                    1
                    for track in tracks
                    if track.index_version != AUDIO_EMBEDDING_VERSION
                )
                if stale:
                    gr.Markdown(
                        f"_Аудиопризнаки устарели у {stale} из {len(tracks)} "
                        "треков: включите «Переиндексировать всё» и нажмите "
                        "«Обновить библиотеку»._"
                    )
                gr.Markdown(f"Показано: **{len(visible)}** из {len(tracks)}")
                with gr.Row(equal_height=True):
                    gr.Markdown("**▶**", scale=0, min_width=36)
                    gr.Markdown("**#**", scale=0, min_width=30)
                    gr.Markdown("**Название**", scale=4)
                    gr.Markdown("**Тип**", scale=1)
                    gr.Markdown("**Жанр**", scale=2)
                    gr.Markdown("**Настроение**", scale=2)
                    gr.Markdown("**Вокал / текст**", scale=3)
                    gr.Markdown("**Длит., с**", scale=1)

                with gr.Column(elem_classes="library-scroll"):
                    for index, track in enumerate(visible, 1):
                        track_id = track.id
                        status = status_map.get(
                            track_id,
                            "has_lyrics" if track.derived.lyrics else "idle",
                        )
                        label, variant = status_label(status)
                        title = escape(track.display_title)
                        duration = (
                            f"{track.derived.duration:.0f}"
                            if track.derived.duration
                            else "—"
                        )
                        vocal_text = vocal_label(track)
                        if track.derived.lyrics:
                            vocal_text += " / текст есть"
                        with gr.Row(equal_height=True):
                            play_button = gr.Button(
                                "▶",
                                size="sm",
                                min_width=36,
                                elem_classes="soundseek-row-play",
                            )
                            play_button.click(
                                fn=lambda tid=track_id: play_track(tid),
                                inputs=None,
                                outputs=[
                                    global_player,
                                    global_audio,
                                    global_meta,
                                ],
                            )
                            gr.Markdown(f"{index}", scale=0, min_width=30)
                            gr.Markdown(title, scale=4)
                            gr.Markdown(
                                track.derived.content_type or "—", scale=1
                            )
                            gr.Markdown(track.derived.genre or "—", scale=2)
                            gr.Markdown(track.derived.mood or "—", scale=2)
                            with gr.Column(scale=3):
                                if status in ("idle", "error", "skipped"):
                                    force = status in ("error", "skipped")
                                    button = gr.Button(
                                        f"{label} ({vocal_text})",
                                        size="sm",
                                        variant=variant,
                                    )
                                    button.click(
                                        fn=lambda tid=track_id, f=force: enqueue_and_status(
                                            tid, f
                                        ),
                                        inputs=None,
                                        outputs=track_status_state,
                                    )
                                else:
                                    gr.Button(
                                        f"{label} ({vocal_text})",
                                        size="sm",
                                        variant=variant,
                                        interactive=False,
                                    )
                            gr.Markdown(duration, scale=1)

            gr.Markdown("---")
            gr.Markdown("### Прослушивание и редактирование")
            with gr.Row():
                track_dropdown = gr.Dropdown(
                    choices=get_track_choices(),
                    label="Выберите трек",
                    scale=3,
                )
                track_status_text = gr.Textbox(
                    label="ID", interactive=False, scale=1
                )
            with gr.Row():
                with gr.Column(scale=2):
                    cover_image = gr.Image(
                        label="Обложка", height=240, interactive=False
                    )
                with gr.Column(scale=3):
                    gr.Markdown(
                        "Трек воспроизводится в глобальном плеере справа. "
                        "Плеер остаётся на месте при переключении вкладок."
                    )
                    edit_play_btn = gr.Button(
                        "▶ Слушать выбранный трек",
                        variant="secondary",
                    )
                    edit_play_btn.click(
                        fn=play_track,
                        inputs=track_status_text,
                        outputs=[
                            global_player,
                            global_audio,
                            global_meta,
                        ],
                    )

            with gr.Accordion("Редактировать теги и метаданные", open=False):
                gr.Markdown("**Теги файла**")
                with gr.Row():
                    edit_title = gr.Textbox(label="Название", scale=2)
                    edit_artist = gr.Textbox(label="Исполнитель", scale=2)
                with gr.Row():
                    edit_album = gr.Textbox(label="Альбом", scale=2)
                    edit_year = gr.Textbox(label="Год", scale=1)
                edit_tag_genre = gr.Textbox(
                    label="Жанр в теге (свободный текст)"
                )

                gr.Markdown("**Вычислено системой**")
                with gr.Row():
                    edit_derived_genre = gr.Dropdown(
                        label="Жанр",
                        choices=GENRE_CHOICES,
                        value="",
                        allow_custom_value=False,
                        scale=1,
                    )
                    edit_derived_mood = gr.Dropdown(
                        label="Настроение",
                        choices=MOOD_CHOICES,
                        value="",
                        allow_custom_value=False,
                        scale=1,
                    )
                edit_lyrics = gr.Textbox(
                    label="Текст песни", lines=8, max_lines=20
                )
                edit_user_notes = gr.Textbox(
                    label="Личная пометка",
                    placeholder="например: для тренировки, любимое, на повтор",
                    lines=2,
                )
                save_btn = gr.Button("Сохранить изменения", variant="primary")
                save_status = gr.Textbox(label="Статус сохранения", interactive=False)
                with gr.Row():
                    retry_btn = gr.Button("Перераспознать текст (Demucs + Whisper)")
                    delete_btn = gr.Button("Удалить из индекса", variant="stop")

            track_dropdown.change(
                fn=load_track_for_edit,
                inputs=track_dropdown,
                outputs=[
                    cover_image,
                    edit_title,
                    edit_artist,
                    edit_album,
                    edit_year,
                    edit_tag_genre,
                    edit_derived_genre,
                    edit_derived_mood,
                    edit_lyrics,
                    edit_user_notes,
                    track_status_text,
                ],
            )
            save_btn.click(
                fn=save_track_edits,
                inputs=[
                    track_status_text,
                    edit_title,
                    edit_artist,
                    edit_album,
                    edit_year,
                    edit_tag_genre,
                    edit_derived_genre,
                    edit_derived_mood,
                    edit_lyrics,
                    edit_user_notes,
                ],
                outputs=[save_status, track_status_state],
            ).then(
                fn=lambda: gr.update(choices=get_track_choices()),
                inputs=None,
                outputs=track_dropdown,
            )
            retry_btn.click(
                fn=retry_enrichment,
                inputs=track_status_text,
                outputs=[save_status, track_status_state],
            )
            delete_btn.click(
                fn=remove_track,
                inputs=track_status_text,
                outputs=[status_msg, track_dropdown, track_status_state],
            )

            add_btn.click(
                fn=add_files_to_library,
                inputs=upload_files,
                outputs=[status_msg, track_dropdown, track_status_state],
            )
            refresh_btn.click(
                fn=refresh_library,
                inputs=force_reindex,
                outputs=[status_msg, track_dropdown, track_status_state],
            )
            enqueue_all_btn.click(
                fn=enqueue_all,
                inputs=None,
                outputs=track_status_state,
            )

            timer = gr.Timer(2.0)
            timer.tick(fn=get_status_map, outputs=track_status_state)

        with gr.Tab("Карта аудиотеки"):
            gr.Markdown(
                "Двумерная проекция CLAP-эмбеддингов (PCA). "
                "Наведите на точку, чтобы увидеть трек; нажмите, чтобы "
                "включить его в глобальном плеере."
            )
            with gr.Column(elem_id="soundseek-map-content"):
                with gr.Row():
                    map_color = gr.Dropdown(
                        choices=[
                            ("по жанру", "genre"),
                            ("по настроению", "mood"),
                            ("по типу контента", "content_type"),
                        ],
                        value="genre",
                        label="Цвет",
                        scale=2,
                    )
                    map_btn = gr.Button("Пересчитать карту", scale=1)
                map_output = gr.HTML(
                    value=update_embedding_map("genre"),
                    js_on_load=MAP_JS,
                    elem_id="soundseek-map-output",
                )
            map_btn.click(
                fn=update_embedding_map,
                inputs=map_color,
                outputs=map_output,
            )
            map_color.change(
                fn=update_embedding_map,
                inputs=map_color,
                outputs=map_output,
            )
            map_output.track_click(
                fn=handle_track_play,
                inputs=None,
                outputs=[global_player, global_audio, global_meta],
            )

        with gr.Tab("Альбомы"):
            with gr.Row():
                gr.Markdown("### Альбомы", scale=4)
                album_refresh = gr.Button("Обновить альбомы", scale=1)
            gr.Markdown(
                "Основные альбомы собраны по типу контента. Отдельно показаны "
                "альбомы, для которых в библиотеке есть минимум два трека с "
                "одинаковыми метаданными. Нажмите на обложку, чтобы увидеть треки."
            )
            album_selected = gr.State("")
            album_detail = gr.HTML(
                value=format_album_detail(None),
                elem_id="soundseek-album-detail",
                js_on_load=PLAY_BUTTON_JS,
            )
            album_output = gr.HTML(
                value=build_albums_view(*album_sections()),
                js_on_load=ALBUM_JS,
                elem_id="soundseek-album-output",
            )
            album_output.album_click(
                fn=handle_album_click,
                inputs=None,
                outputs=[album_selected, album_detail],
            )
            album_detail.track_play(
                fn=handle_track_play,
                inputs=None,
                outputs=[global_player, global_audio, global_meta],
            )
            album_refresh.click(
                fn=update_albums,
                inputs=album_selected,
                outputs=[album_output, album_detail],
            )

        with gr.Tab("Плейлист"):
            gr.Markdown(
                "Соберите последовательность по настроению. "
                "Можно задать начальное и конечное настроение для плавного перехода."
            )
            with gr.Row():
                playlist_target = gr.Dropdown(
                    choices=MOOD_CHOICES,
                    value="calm",
                    label="Целевое настроение",
                    scale=2,
                )
                playlist_start = gr.Dropdown(
                    choices=MOOD_CHOICES,
                    value="",
                    label="Начало (необязательно)",
                    scale=2,
                )
                playlist_end = gr.Dropdown(
                    choices=MOOD_CHOICES,
                    value="",
                    label="Конец (необязательно)",
                    scale=2,
                )
            with gr.Row():
                playlist_genre = gr.Dropdown(
                    choices=GENRE_CHOICES,
                    value="",
                    label="Жанр (необязательно)",
                    scale=2,
                )
                playlist_length = gr.Slider(
                    3, 30, value=10, step=1, label="Длина", scale=2
                )
                playlist_btn = gr.Button("Собрать плейлист", variant="primary", scale=1)
            playlist_output = gr.HTML(js_on_load=PLAY_BUTTON_JS)
            playlist_output.track_play(
                fn=handle_track_play,
                inputs=None,
                outputs=[global_player, global_audio, global_meta],
            )
            playlist_btn.click(
                fn=make_playlist,
                inputs=[
                    playlist_target,
                    playlist_start,
                    playlist_end,
                    playlist_length,
                    playlist_genre,
                ],
                outputs=playlist_output,
            )


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True,
        theme=gr.themes.Soft(),
        css=APP_CSS,
    )
