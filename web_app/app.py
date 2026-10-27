import os
import sys
import shutil
import threading
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["DEMUCS_DEVICE"] = "cpu"
os.environ["PATH"] = r"C:\Users\Adli\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin" + os.pathsep + os.environ["PATH"]

import gradio as gr

from soundseek_core import AudioIndexer
from soundseek_core.ontology import Ontology
from soundseek_core.searcher import Searcher


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRACKS_DIR = PROJECT_ROOT / "data" / "tracks"
INDEXES_PATH = PROJECT_ROOT / "data" / "indexes" / "library"

TRACKS_DIR.mkdir(parents=True, exist_ok=True)
(PROJECT_ROOT / "data" / "indexes").mkdir(parents=True, exist_ok=True)
(PROJECT_ROOT / "data" / "covers").mkdir(parents=True, exist_ok=True)


# ---------- Инициализация ----------
print("Инициализация SoundSeek...")
ontology = Ontology()
indexer = AudioIndexer(db_path=str(INDEXES_PATH), ontology=ontology)
searcher = Searcher(indexer, ontology)
print("Готово.")


# ---------- Очередь фонового обогащения ----------
_worker = {
    "queue": deque(),
    "running": None,
    "done": {},
    "lock": threading.Lock(),
    "thread_started": False,
}


def _worker_loop():
    while True:
        with _worker["lock"]:
            if not _worker["queue"]:
                _worker["running"] = None
                _worker["thread_started"] = False
                break
            track_id = _worker["queue"].popleft()
            _worker["running"] = track_id

        track = next((t for t in indexer.db.tracks if t.id == track_id), None)
        if not track:
            with _worker["lock"]:
                _worker["done"][track_id] = "error"
            continue

        try:
            indexer.enrich_single_track(track)
            with _worker["lock"]:
                _worker["done"][track_id] = "done"
        except Exception as e:
            print(f"Ошибка enrich для {track_id}: {e}")
            with _worker["lock"]:
                _worker["done"][track_id] = "error"


def _enqueue(track_id: str):
    with _worker["lock"]:
        if track_id == _worker["running"]:
            return
        if track_id in _worker["done"]:
            return
        if track_id in _worker["queue"]:
            return
        _worker["queue"].append(track_id)
        if not _worker["thread_started"]:
            _worker["thread_started"] = True
            threading.Thread(target=_worker_loop, daemon=True).start()


def _get_status_map() -> dict:
    with _worker["lock"]:
        queue_set = set(_worker["queue"])
        running = _worker["running"]
        done = dict(_worker["done"])

    status = {}
    for t in indexer.db.tracks:
        tid = t.id
        if tid == running:
            status[tid] = "running"
        elif tid in queue_set:
            status[tid] = "queued"
        elif tid in done:
            status[tid] = done[tid]
        elif t.derived.lyrics:
            status[tid] = "has_lyrics"
        else:
            status[tid] = "idle"
    return status


def _on_enqueue_click(track_id: str):
    _enqueue(track_id)
    return _get_status_map()


def _reset_worker_state():
    with _worker["lock"]:
        _worker["queue"].clear()
        _worker["running"] = None
        _worker["done"] = {}


# ---------- Форматирование результатов поиска ----------
def format_results(results) -> str:
    if not results:
        return "<p style='color:#333;'><i>Ничего не найдено.</i></p>"

    html = "<div style='color:#1a2b47;'>"
    for i, r in enumerate(results, 1):
        track = r["track"]
        title = track.tags.title or track.id
        explanations = "".join(
            f"<li style='color:#333;'>{e}</li>" for e in r["explanations"]
        )
        html += f"""
        <div style="border:1px solid #d0d7e2; border-radius:8px; padding:12px;
                    margin-bottom:12px; background:#ffffff; color:#1a2b47;">
            <div style="font-size:16px; font-weight:600;">{i}. {title}</div>
            <div style="color:#555; font-size:13px; margin:4px 0;">
                Тип: <b>{track.derived.content_type or "—"}</b> |
                Жанр: <b>{track.derived.genre or "—"}</b> |
                Настроение: <b>{track.derived.mood or "—"}</b> |
                Вокал: <b>{"да" if track.derived.has_vocal else "нет"}</b>
            </div>
            <div style="font-size:13px; margin:6px 0;">
                Скор: <b>{r['final_score']:.3f}</b>
                <span style="color:#888;">(база: {r['base_score']:.3f})</span>
            </div>
            <div style="font-size:13px; margin-top:6px;">
                <b>Почему найден:</b>
                <ul style="margin:4px 0 0 20px;">{explanations}</ul>
            </div>
        </div>
        """
    return html + "</div>"


# ---------- Данные для UI ----------
def get_track_choices():
    return [t.id for t in indexer.db.tracks]


GENRE_CHOICES = [""] + sorted(ontology.genres.keys())
MOOD_CHOICES = [""] + sorted(ontology.moods.keys())


# ---------- Добавление / обновление ----------
def add_files_to_library(files):
    if not files:
        return "Файлы не выбраны.", gr.update(choices=get_track_choices(), value=None)

    added = []
    skipped = []
    for f in files:
        src = Path(f.name)
        dst = TRACKS_DIR / src.name
        if dst.exists():
            skipped.append(src.name)
            continue
        shutil.copy2(src, dst)
        added.append(src.name)

    indexer.index_folder_light(str(TRACKS_DIR))
    msg = f"Добавлено: {len(added)}. Пропущено: {len(skipped)}."
    return msg, gr.update(choices=get_track_choices(), value=None)


def refresh_library(force: bool):
    if force:
        indexer.reset_db()
        _reset_worker_state()
    n = indexer.index_folder_light(str(TRACKS_DIR))
    prefix = "Переиндексировано" if force else "Обновлено"
    return f"{prefix}. Всего файлов: {n}.", gr.update(choices=get_track_choices(), value=None)


# ---------- Карточка трека + форма редактирования ----------
def load_track_for_edit(track_id):
    empty = (None, None, "", "", "", "", "", "", "", "", "", "")
    if not track_id:
        return empty
    t = next((t for t in indexer.db.tracks if t.id == track_id), None)
    if not t:
        return empty

    cover = t.tags.cover_path if t.tags.cover_path and Path(t.tags.cover_path).exists() else None
    year_str = str(t.tags.year) if t.tags.year else ""

    return (
        t.path,
        cover,
        t.tags.title,
        t.tags.artist,
        t.tags.album,
        year_str,
        t.tags.genre,
        t.derived.genre,
        t.derived.mood,
        t.derived.lyrics,
        t.derived.user_notes,
        t.id,
    )


def save_track_edits(track_id, title, artist, album, year_str, tag_genre, derived_genre, derived_mood, lyrics, user_notes):
    if not track_id:
        return "Не выбран трек."

    year = None
    if year_str and str(year_str).strip():
        try:
            year = int(str(year_str).strip())
        except ValueError:
            year = None

    track = indexer.update_track_fields(
        track_id,
        title=title, artist=artist, album=album, year=year,
        tag_genre=tag_genre,
        derived_genre=derived_genre,
        derived_mood=derived_mood,
        lyrics=lyrics,
        user_notes=user_notes,
    )
    if not track:
        return f"Трек {track_id} не найден."
    return f"Сохранено: {track_id}"


# ---------- Поиск ----------
def handle_text_search(query: str):
    if not query.strip():
        return "<p><i>Введите запрос.</i></p>"
    return format_results(searcher.search(query, top_k=5))


def handle_audio_search(audio_path):
    if audio_path is None:
        return "<p><i>Запишите или загрузите аудио.</i></p>"
    return format_results(searcher.search_by_audio(audio_path, top_k=5))


STATUS_LABELS = {
    "idle":       ("Распознать текст",   "secondary"),
    "queued":     ("⏳ В очереди",       "secondary"),
    "running":    ("⏳ Распознавание...", "primary"),
    "done":       ("✅ Готово",          "secondary"),
    "error":      ("❌ Ошибка",          "stop"),
    "has_lyrics": ("✅ Уже есть",        "secondary"),
}


def _vocal_cell_text(track) -> str:
    if track.derived.has_vocal:
        return "да"
    if track.derived.lyrics:
        return "да"
    return "нет"


# ---------- Интерфейс ----------
with gr.Blocks(title="SoundSeek", theme=gr.themes.Soft(), css="body { color-scheme: light; }") as demo:
    gr.Markdown("# 🎵 SoundSeek\nЛокальная гибридная интеллектуальная система поиска в аудиотеке.")

    track_status_state = gr.State(_get_status_map())
    library_refresh_state = gr.State(0)  # счётчик, чтобы перерисовывать таблицу

    with gr.Tabs():

        # === Поиск по тексту ===
        with gr.Tab("Поиск по тексту"):
            with gr.Row():
                text_input = gr.Textbox(
                    label="Что ищем?",
                    placeholder="например: грустный рок, lonely day, весёлый панк",
                    scale=4,
                )
                text_btn = gr.Button("Найти", variant="primary", scale=1)

            text_output = gr.HTML(label="Результаты")
            text_btn.click(handle_text_search, inputs=text_input, outputs=text_output)
            text_input.submit(handle_text_search, inputs=text_input, outputs=text_output)

            gr.Examples(
                examples=["lonely day", "грустный рок", "весёлый панк", "ambient calm music"],
                inputs=text_input,
            )

        # === Поиск по напеванию ===
        with gr.Tab("Поиск по напеванию"):
            gr.Markdown("Запишите напевание или загрузите аудиофрагмент.")
            audio_input = gr.Audio(sources=["microphone", "upload"], type="filepath", label="Напевание")
            audio_btn = gr.Button("Найти похожее", variant="primary")
            audio_output = gr.HTML(label="Результаты")
            audio_btn.click(handle_audio_search, inputs=audio_input, outputs=audio_output)

        # === Библиотека ===
        with gr.Tab("Библиотека"):
            gr.Markdown("### Добавление треков")
            gr.Markdown(
                "Выберите аудиофайлы. Они будут скопированы в `data/tracks/` и проиндексированы."
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
                    force_reindex = gr.Checkbox(
                        label="Переиндексировать всё",
                        value=False,
                        info="Удаляет старые индексы и обрабатывает все треки заново",
                    )
                    refresh_btn = gr.Button("Обновить библиотеку")

            status_msg = gr.Textbox(label="Статус", interactive=False)

            gr.Markdown("### Треки в библиотеке")
            gr.Markdown(
                "_Кнопка в колонке «Вокал» запускает распознавание текста. "
                "Если обработчик занят — задача встаёт в очередь._"
            )

            @gr.render(inputs=[track_status_state, library_refresh_state])
            def render_tracks(status_map, _refresh_counter):
                if not indexer.db.tracks:
                    gr.Markdown("_Пока нет треков. Добавьте файлы выше._")
                    return

                if not status_map:
                    status_map = {}

                # Заголовок таблицы
                with gr.Row(equal_height=True):
                    gr.Markdown("**#**", scale=0, min_width=30)
                    gr.Markdown("**Название**", scale=4)
                    gr.Markdown("**Тип**", scale=1)
                    gr.Markdown("**Жанр**", scale=2)
                    gr.Markdown("**Настроение**", scale=2)
                    gr.Markdown("**Вокал**", scale=2)
                    gr.Markdown("**Текст**", scale=1)
                    gr.Markdown("**Длит., с**", scale=1)

                for i, t in enumerate(indexer.db.tracks, 1):
                    tid = t.id
                    status = status_map.get(tid, "has_lyrics" if t.derived.lyrics else "idle")
                    title = t.tags.title or tid
                    has_text = "да" if t.derived.lyrics else "—"
                    dur = f"{t.derived.duration:.0f}" if t.derived.duration else "—"
                    vocal_mark = _vocal_cell_text(t)
                    label, variant = STATUS_LABELS.get(status, ("Распознать текст", "secondary"))

                    with gr.Row(equal_height=True):
                        gr.Markdown(f"{i}", scale=0, min_width=30)
                        gr.Markdown(title, scale=4)
                        gr.Markdown(t.derived.content_type or "—", scale=1)
                        gr.Markdown(t.derived.genre or "—", scale=2)
                        gr.Markdown(t.derived.mood or "—", scale=2)

                        with gr.Column(scale=2):
                            if status == "idle":
                                btn = gr.Button(
                                    f"{label} ({vocal_mark})",
                                    size="sm",
                                    variant=variant,
                                )
                                btn.click(
                                    fn=lambda t_id=tid: _on_enqueue_click(t_id),
                                    inputs=None,
                                    outputs=track_status_state,
                                )
                            else:
                                gr.Button(
                                    f"{label} ({vocal_mark})",
                                    size="sm",
                                    variant=variant,
                                    interactive=False,
                                )

                        gr.Markdown(has_text, scale=1)
                        gr.Markdown(dur, scale=1)

            gr.Markdown("---")
            gr.Markdown("### Прослушивание и редактирование трека")

            with gr.Row():
                track_dropdown = gr.Dropdown(
                    choices=get_track_choices(),
                    label="Выберите трек",
                    scale=2,
                )
                track_status_text = gr.Textbox(
                    label="Текущий ID",
                    interactive=False,
                    scale=1,
                )

            with gr.Row():
                with gr.Column(scale=2):
                    cover_image = gr.Image(label="Обложка", height=240, interactive=False)
                with gr.Column(scale=3):
                    track_player = gr.Audio(interactive=False, label="Воспроизведение")

            # Форма редактирования
            with gr.Accordion("✏️ Редактировать теги и метаданные", open=False):
                gr.Markdown("**Теги файла**")
                with gr.Row():
                    edit_title = gr.Textbox(label="Название", scale=2)
                    edit_artist = gr.Textbox(label="Исполнитель", scale=2)
                with gr.Row():
                    edit_album = gr.Textbox(label="Альбом", scale=2)
                    edit_year = gr.Textbox(label="Год", scale=1)
                edit_tag_genre = gr.Textbox(label="Жанр в теге (свободный текст)")

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
                    label="Текст песни",
                    lines=8,
                    max_lines=20,
                )
                edit_user_notes = gr.Textbox(
                    label="Личная пометка",
                    placeholder="например: для тренировки, любимое, на повтор",
                    lines=2,
                )

                save_btn = gr.Button("Сохранить изменения", variant="primary")
                save_status = gr.Textbox(label="Статус сохранения", interactive=False)

            # Связки
            track_dropdown.change(
                fn=load_track_for_edit,
                inputs=track_dropdown,
                outputs=[
                    track_player,
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
                outputs=save_status,
            ).then(
                _get_status_map,
                outputs=track_status_state,
            )

            add_btn.click(
                add_files_to_library,
                inputs=upload_files,
                outputs=[status_msg, track_dropdown],
            ).then(
                _get_status_map,
                outputs=track_status_state,
            )

            refresh_btn.click(
                refresh_library,
                inputs=force_reindex,
                outputs=[status_msg, track_dropdown],
            ).then(
                _get_status_map,
                outputs=track_status_state,
            )

            # Таймер: каждые 2 секунды подтягивает статусы
            timer = gr.Timer(2.0)
            timer.tick(
                _get_status_map,
                outputs=track_status_state,
            )


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)