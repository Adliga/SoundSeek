import os
import sys
import shutil
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


# ---------- Инициализация ----------
print("Инициализация SoundSeek...")
ontology = Ontology()
indexer = AudioIndexer(db_path=str(INDEXES_PATH), ontology=ontology)
searcher = Searcher(indexer, ontology)
print("Готово.")


# ---------- Формат вывода результатов поиска ----------
def format_results(results) -> str:
    if not results:
        return "<p style='color:#333;'><i>Ничего не найдено.</i></p>"

    html = "<div style='color:#1a2b47;'>"
    for i, r in enumerate(results, 1):
        track = r["track"]
        explanations = "".join(
            f"<li style='color:#333;'>{e}</li>" for e in r["explanations"]
        )
        html += f"""
        <div style="border:1px solid #d0d7e2; border-radius:8px; padding:12px;
                    margin-bottom:12px; background:#ffffff; color:#1a2b47;">
            <div style="font-size:16px; font-weight:600;">{i}. {track.id}</div>
            <div style="color:#555; font-size:13px; margin:4px 0;">
                Жанр: <b>{track.genre or "—"}</b> |
                Настроение: <b>{track.mood or "—"}</b> |
                Вокал: <b>{"да" if track.has_vocal else "нет"}</b>
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


# ---------- Библиотека ----------
def get_library_table():
    """Возвращает данные для таблицы библиотеки."""
    rows = []
    for i, t in enumerate(indexer.db.tracks, 1):
        rows.append([
            i,
            t.id,
            t.genre or "—",
            t.mood or "—",
            "да" if t.has_vocal else "нет",
            f"{t.duration:.0f}" if t.duration else "—",
        ])
    return rows


def get_track_choices():
    return [t.id for t in indexer.db.tracks]


def add_files_to_library(files):
    """Копирует загруженные файлы в data/tracks/ и индексирует новые."""
    if not files:
        return "Файлы не выбраны.", get_library_table(), gr.update(choices=get_track_choices())

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

    # Инкрементальная индексация — существующие пропустятся
    indexer.index_folder_light(str(TRACKS_DIR))

    msg = f"Добавлено: {len(added)}. Пропущено (уже есть): {len(skipped)}."
    return msg, get_library_table(), gr.update(choices=get_track_choices())


def refresh_library():
    """Переиндексировать папку tracks — на случай, если файлы добавили вручную."""
    n = indexer.index_folder_light(str(TRACKS_DIR))
    return f"Обновлено. Всего файлов: {n}.", get_library_table(), gr.update(choices=get_track_choices())


def show_track_info(track_id):
    """Возвращает путь к аудиофайлу, путь к обложке и текстовую информацию."""
    if not track_id:
        return None, None, ""
    for t in indexer.db.tracks:
        if t.id == track_id:
            info_parts = []
            info_parts.append(f"**ID:** `{t.id}`")
            if t.title:
                info_parts.append(f"**Название:** {t.title}")
            if t.artist:
                info_parts.append(f"**Исполнитель:** {t.artist}")
            if t.album:
                info_parts.append(f"**Альбом:** {t.album}")
            if t.year:
                info_parts.append(f"**Год:** {t.year}")
            info_parts.append(f"**Жанр:** {t.genre or '—'}")
            info_parts.append(f"**Настроение:** {t.mood or '—'}")
            info_parts.append(f"**Вокал:** {'да' if t.has_vocal else 'нет'}")
            info_parts.append(f"**Длительность:** {t.duration:.1f} сек")
            info_parts.append(f"**Путь:** `{t.path}`")

            if t.lyrics:
                info_parts.append(f"**Текст песни:**\n\n{t.lyrics[:800]}")

            cover = t.cover_path if t.cover_path and Path(t.cover_path).exists() else None
            return t.path, cover, "\n\n".join(info_parts)
    return None, None, ""


# ---------- Обработчики поиска ----------
def handle_text_search(query: str):
    if not query.strip():
        return "<p><i>Введите запрос.</i></p>"
    return format_results(searcher.search(query, top_k=5))


def handle_audio_search(audio_path):
    if audio_path is None:
        return "<p><i>Запишите или загрузите аудио.</i></p>"
    return format_results(searcher.search_by_audio(audio_path, top_k=5))


# ---------- Интерфейс ----------
with gr.Blocks(title="SoundSeek", theme=gr.themes.Soft(), css="body { color-scheme: light; }") as demo:
    gr.Markdown("# 🎵 SoundSeek\nЛокальная гибридная интеллектуальная система поиска в аудиотеке.")

    with gr.Tabs():

        # === Вкладка 1: текстовый поиск ===
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

        # === Вкладка 2: поиск по аудио ===
        with gr.Tab("Поиск по напеванию"):
            gr.Markdown("Запишите напевание или загрузите аудиофрагмент.")
            audio_input = gr.Audio(sources=["microphone", "upload"], type="filepath", label="Напевание")
            audio_btn = gr.Button("Найти похожее", variant="primary")
            audio_output = gr.HTML(label="Результаты")
            audio_btn.click(handle_audio_search, inputs=audio_input, outputs=audio_output)

        # === Вкладка 3: библиотека ===
        with gr.Tab("Библиотека"):
            gr.Markdown("### Добавление треков")
            gr.Markdown(
                "Выберите аудиофайлы на компьютере. Они будут скопированы в `data/tracks/` "
                "и автоматически проиндексированы."
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

            status_msg = gr.Textbox(label="Статус", interactive=False)

            gr.Markdown("### Все треки в библиотеке")

            library_table = gr.Dataframe(
                headers=["#", "ID", "Жанр", "Настроение", "Вокал", "Длит., с"],
                datatype=["number", "str", "str", "str", "str", "str"],
                value=get_library_table(),
                interactive=False,
                wrap=True,
            )

            gr.Markdown("### Прослушать трек")
            with gr.Row():
                track_dropdown = gr.Dropdown(
                    choices=get_track_choices(),
                    label="Выберите трек",
                    scale=1,
                )
                with gr.Column(scale=2):
                    cover_image = gr.Image(label="Обложка", height=240, interactive=False)
                with gr.Column(scale=3):
                    track_info = gr.Markdown("")
                    track_player = gr.Audio(interactive=False, label="Воспроизведение")

            track_dropdown.change(
                show_track_info,
                inputs=track_dropdown,
                outputs=[track_player, cover_image, track_info],
            )

            add_btn.click(
                add_files_to_library,
                inputs=upload_files,
                outputs=[status_msg, library_table, track_dropdown],
            )
            refresh_btn.click(
                refresh_library,
                outputs=[status_msg, library_table, track_dropdown],
            )


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)


# import os
# import sys
# from pathlib import Path

# sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
# os.environ["DEMUCS_DEVICE"] = "cpu"
# os.environ["PATH"] = r"C:\Users\Adli\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin" + os.pathsep + os.environ["PATH"]

# import gradio as gr

# from soundseek_core import AudioIndexer
# from soundseek_core.ontology import Ontology
# from soundseek_core.searcher import Searcher


# # ---------- Инициализация системы ----------
# print("Инициализация SoundSeek...")
# ontology = Ontology()
# indexer = AudioIndexer(db_path="data/indexes/library", ontology=ontology)
# searcher = Searcher(indexer, ontology)
# print("Готово к работе.")


# # ---------- Формирование HTML-ответа ----------
# def format_results(results) -> str:
#     if not results:
#         return "<p style='color:#333;'><i>Ничего не найдено.</i></p>"

#     html = "<div style='color:#1a2b47;'>"
#     for i, r in enumerate(results, 1):
#         track = r["track"]
#         explanations = "".join(
#             f"<li style='color:#333;'>{e}</li>" for e in r["explanations"]
#         )
#         html += f"""
#         <div style="border:1px solid #d0d7e2; border-radius:8px; padding:12px;
#                     margin-bottom:12px; background:#ffffff; color:#1a2b47;">
#             <div style="font-size:16px; font-weight:600; color:#1a2b47;">
#                 {i}. {track.id}
#             </div>
#             <div style="color:#555; font-size:13px; margin:4px 0;">
#                 Жанр: <b style="color:#1a2b47;">{track.genre or "—"}</b> &nbsp;|&nbsp;
#                 Настроение: <b style="color:#1a2b47;">{track.mood or "—"}</b> &nbsp;|&nbsp;
#                 Вокал: <b style="color:#1a2b47;">{"да" if track.has_vocal else "нет"}</b>
#             </div>
#             <div style="font-size:13px; color:#333; margin:6px 0;">
#                 Итоговый скор: <b style="color:#1a2b47;">{r['final_score']:.3f}</b>
#                 <span style="color:#888;">(базовый: {r['base_score']:.3f})</span>
#             </div>
#             <div style="font-size:13px; margin-top:6px; color:#333;">
#                 <b style="color:#1a2b47;">Почему найден:</b>
#                 <ul style="margin:4px 0 0 20px;">{explanations}</ul>
#             </div>
#         </div>
#         """
#     html += "</div>"
#     return html


# # ---------- Обработчики ----------
# def handle_text_search(query: str):
#     if not query.strip():
#         return "<p><i>Введите запрос.</i></p>"
#     results = searcher.search(query, top_k=5)
#     return format_results(results)


# def handle_audio_search(audio_path):
#     if audio_path is None:
#         return "<p><i>Запишите или загрузите аудио.</i></p>"
#     results = searcher.search_by_audio(audio_path, top_k=5)
#     return format_results(results)


# # ---------- Интерфейс ----------
# with gr.Blocks(title="SoundSeek", theme=gr.themes.Soft()) as demo:
#     gr.Markdown(
#         """
#         # 🎵 SoundSeek
#         Локальная гибридная интеллектуальная система поиска в аудиотеке.
#         Ищите по описанию, настроению, названию или напевайте мелодию.
#         """
#     )

#     with gr.Tabs():
#         # --- Вкладка 1: текстовый поиск ---
#         with gr.Tab("Поиск по тексту"):
#             with gr.Row():
#                 text_input = gr.Textbox(
#                     label="Что ищем?",
#                     placeholder="например: грустный рок, lonely day, весёлый панк",
#                     lines=1,
#                     scale=4,
#                 )
#                 text_btn = gr.Button("Найти", variant="primary", scale=1)

#             text_output = gr.HTML(label="Результаты")

#             text_btn.click(handle_text_search, inputs=text_input, outputs=text_output)
#             text_input.submit(handle_text_search, inputs=text_input, outputs=text_output)

#             gr.Examples(
#                 examples=[
#                     "lonely day",
#                     "грустный рок",
#                     "весёлый панк",
#                     "ambient calm music",
#                     "тяжёлый метал",
#                 ],
#                 inputs=text_input,
#             )

#         # --- Вкладка 2: поиск по аудио ---
#         with gr.Tab("Поиск по напеванию"):
#             gr.Markdown(
#                 "Запишите напевание через микрофон или загрузите короткий аудиофрагмент."
#             )
#             audio_input = gr.Audio(
#                 sources=["microphone", "upload"],
#                 type="filepath",
#                 label="Напевание или фрагмент",
#             )
#             audio_btn = gr.Button("Найти похожее", variant="primary")

#             audio_output = gr.HTML(label="Результаты")

#             audio_btn.click(handle_audio_search, inputs=audio_input, outputs=audio_output)


# if __name__ == "__main__":
#     demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)