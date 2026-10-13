import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["DEMUCS_DEVICE"] = "cpu"
os.environ["PATH"] = r"C:\Users\Adli\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin" + os.pathsep + os.environ["PATH"]

import gradio as gr

from soundseek_core import AudioIndexer
from soundseek_core.ontology import Ontology
from soundseek_core.searcher import Searcher


# ---------- Инициализация системы ----------
print("Инициализация SoundSeek...")
ontology = Ontology()
indexer = AudioIndexer(db_path="data/library", ontology=ontology)
searcher = Searcher(indexer, ontology)
print("Готово к работе.")


# ---------- Формирование HTML-ответа ----------
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
            <div style="font-size:16px; font-weight:600; color:#1a2b47;">
                {i}. {track.id}
            </div>
            <div style="color:#555; font-size:13px; margin:4px 0;">
                Жанр: <b style="color:#1a2b47;">{track.genre or "—"}</b> &nbsp;|&nbsp;
                Настроение: <b style="color:#1a2b47;">{track.mood or "—"}</b> &nbsp;|&nbsp;
                Вокал: <b style="color:#1a2b47;">{"да" if track.has_vocal else "нет"}</b>
            </div>
            <div style="font-size:13px; color:#333; margin:6px 0;">
                Итоговый скор: <b style="color:#1a2b47;">{r['final_score']:.3f}</b>
                <span style="color:#888;">(базовый: {r['base_score']:.3f})</span>
            </div>
            <div style="font-size:13px; margin-top:6px; color:#333;">
                <b style="color:#1a2b47;">Почему найден:</b>
                <ul style="margin:4px 0 0 20px;">{explanations}</ul>
            </div>
        </div>
        """
    html += "</div>"
    return html


# ---------- Обработчики ----------
def handle_text_search(query: str):
    if not query.strip():
        return "<p><i>Введите запрос.</i></p>"
    results = searcher.search(query, top_k=5)
    return format_results(results)


def handle_audio_search(audio_path):
    if audio_path is None:
        return "<p><i>Запишите или загрузите аудио.</i></p>"
    results = searcher.search_by_audio(audio_path, top_k=5)
    return format_results(results)


# ---------- Интерфейс ----------
with gr.Blocks(title="SoundSeek", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 🎵 SoundSeek
        Локальная гибридная интеллектуальная система поиска в аудиотеке.
        Ищите по описанию, настроению, названию или напевайте мелодию.
        """
    )

    with gr.Tabs():
        # --- Вкладка 1: текстовый поиск ---
        with gr.Tab("Поиск по тексту"):
            with gr.Row():
                text_input = gr.Textbox(
                    label="Что ищем?",
                    placeholder="например: грустный рок, lonely day, весёлый панк",
                    lines=1,
                    scale=4,
                )
                text_btn = gr.Button("Найти", variant="primary", scale=1)

            text_output = gr.HTML(label="Результаты")

            text_btn.click(handle_text_search, inputs=text_input, outputs=text_output)
            text_input.submit(handle_text_search, inputs=text_input, outputs=text_output)

            gr.Examples(
                examples=[
                    "lonely day",
                    "грустный рок",
                    "весёлый панк",
                    "ambient calm music",
                    "тяжёлый метал",
                ],
                inputs=text_input,
            )

        # --- Вкладка 2: поиск по аудио ---
        with gr.Tab("Поиск по напеванию"):
            gr.Markdown(
                "Запишите напевание через микрофон или загрузите короткий аудиофрагмент."
            )
            audio_input = gr.Audio(
                sources=["microphone", "upload"],
                type="filepath",
                label="Напевание или фрагмент",
            )
            audio_btn = gr.Button("Найти похожее", variant="primary")

            audio_output = gr.HTML(label="Результаты")

            audio_btn.click(handle_audio_search, inputs=audio_input, outputs=audio_output)


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)