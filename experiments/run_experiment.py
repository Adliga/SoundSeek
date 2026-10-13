import os

# Путь к ffmpeg (замените на свой, если отличается)
FFMPEG_BIN = r"C:\Users\Adli\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
os.environ["PATH"] = FFMPEG_BIN + os.pathsep + os.environ["PATH"]
os.environ["DEMUCS_DEVICE"] = "cpu"

import time
import json
import warnings
from pathlib import Path

import whisper
import jiwer
from demucs_onnx import separate_stem

warnings.filterwarnings("ignore")

# ---------- Конфигурация ----------
TRACKS = {
    "lonely_day": {
        "audio": "data/lonely_day.mp3",
        "reference": "experiments/references/lonely_day.txt",
    },
    "korol_i_shut": {
        "audio": "data/korol_i_shut.mp3",
        "reference": "experiments/references/korol_i_shut.txt",
    },
}

MODELS = ["base", "small"]
CONDITIONS = ["mix", "vocals"]

SEPARATED_DIR = Path("experiments/separated")
RESULTS_DIR = Path("experiments/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
SEPARATED_DIR.mkdir(parents=True, exist_ok=True)


# ---------- Нормализация текста ----------
def normalize(text: str) -> str:
    text = text.lower()
    # Убираем пунктуацию (кроме апострофов)
    for ch in ".,!?;:—-\"()[]«»":
        text = text.replace(ch, " ")
    text = " ".join(text.split())
    return text


# ---------- Отделение вокала ----------
def separate_vocals(audio_path: str, track_name: str) -> str:
    out_path = SEPARATED_DIR / f"{track_name}_vocals.wav"
    if out_path.exists():
        print(f"  [Demucs] пропуск, файл уже есть: {out_path}")
        return str(out_path)

    print(f"  [Demucs] отделение вокала...")
    t0 = time.time()
    separate_stem(audio_path, stem="vocals", output_dir=str(SEPARATED_DIR))
    elapsed = time.time() - t0
    print(f"  [Demucs] готово за {elapsed:.1f} сек")

    # demucs-onnx сохраняет файл как vocals.wav — переименуем
    default_out = SEPARATED_DIR / "vocals.wav"
    if default_out.exists() and not out_path.exists():
        default_out.rename(out_path)
    return str(out_path)


# ---------- Запуск Whisper ----------
def transcribe(model, audio_path: str) -> tuple:
    t0 = time.time()
    result = model.transcribe(audio_path, language=None)
    elapsed = time.time() - t0
    return result["text"].strip(), result["language"], elapsed


# ---------- Основной цикл ----------
def main():
    # Готовим Demucs для каждого трека заранее
    print("=" * 70)
    print("ЭТАП 1. Отделение вокала через Demucs")
    print("=" * 70)
    separated_paths = {}
    for track_name, cfg in TRACKS.items():
        print(f"\nТрек: {track_name}")
        separated_paths[track_name] = separate_vocals(cfg["audio"], track_name)

    # Прогоняем каждый вариант
    print("\n" + "=" * 70)
    print("ЭТАП 2. Распознавание речи")
    print("=" * 70)

    # Загружаем эталоны
    references = {}
    for track_name, cfg in TRACKS.items():
        ref_text = Path(cfg["reference"]).read_text(encoding="utf-8")
        references[track_name] = normalize(ref_text)

    # Загружаем модели по очереди (экономим память)
    results = []

    for model_size in MODELS:
        print(f"\n--- Whisper {model_size} ---")
        model = whisper.load_model(model_size)

        for track_name, cfg in TRACKS.items():
            for condition in CONDITIONS:
                audio_path = cfg["audio"] if condition == "mix" else separated_paths[track_name]

                print(f"  [{track_name} | {condition} | {model_size}]", end=" ")
                text, lang, elapsed = transcribe(model, audio_path)
                print(f"lang={lang}, time={elapsed:.1f}s")

                # Сохраняем распознанный текст
                out_name = f"{track_name}__{condition}__{model_size}.txt"
                (RESULTS_DIR / out_name).write_text(text, encoding="utf-8")

                # Считаем метрики
                hyp = normalize(text)
                ref = references[track_name]

                wer = jiwer.wer(ref, hyp)
                cer = jiwer.cer(ref, hyp)

                results.append({
                    "track": track_name,
                    "condition": condition,
                    "model": model_size,
                    "language": lang,
                    "time_sec": round(elapsed, 1),
                    "wer": round(wer, 4),
                    "cer": round(cer, 4),
                })

        # Освобождаем память
        del model

    # ---------- Сводка ----------
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТЫ")
    print("=" * 70)

    header = f"{'Трек':<15} {'Условие':<10} {'Модель':<8} {'WER':>8} {'CER':>8} {'Время, с':>10}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r['track']:<15} {r['condition']:<10} {r['model']:<8} "
              f"{r['wer']:>8.4f} {r['cer']:>8.4f} {r['time_sec']:>10.1f}")

    # Сохраняем в JSON для отчёта
    out_json = RESULTS_DIR / "results.json"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nРезультаты сохранены: {out_json}")


if __name__ == "__main__":
    main()