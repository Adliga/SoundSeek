"""Эксперимент WER/CER: Whisper на миксе и на вокальной дорожке Demucs."""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import jiwer
import whisper
from demucs_onnx import separate_stem

from soundseek_core.config import TRACKS_DIR, configure_runtime

warnings.filterwarnings("ignore")
configure_runtime()

EXPERIMENTS_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = EXPERIMENTS_DIR / "references"
SEPARATED_DIR = EXPERIMENTS_DIR / "separated"
RESULTS_DIR = EXPERIMENTS_DIR / "results"

TRACKS = {
    "lonely_day": {
        "audio": TRACKS_DIR / "lonely_day.mp3",
        "reference": REFERENCES_DIR / "lonely_day.txt",
    },
    "korol_i_shut": {
        "audio": TRACKS_DIR / "korol_i_shut.mp3",
        "reference": REFERENCES_DIR / "korol_i_shut.txt",
    },
}
MODELS = ["base", "small"]
CONDITIONS = ["mix", "vocals"]


def normalize(text: str) -> str:
    text = text.lower()
    for char in ".,!?;:—-\"()[]«»":
        text = text.replace(char, " ")
    return " ".join(text.split())


def separate_vocals(audio_path: Path, track_name: str, force: bool = False) -> Path:
    out_path = SEPARATED_DIR / f"{track_name}_vocals.wav"
    if out_path.exists() and not force:
        print(f"  [Demucs] пропуск: {out_path}")
        return out_path

    print("  [Demucs] отделение вокала...")
    start = time.time()
    separate_stem(str(audio_path), stem="vocals", output_dir=str(SEPARATED_DIR))
    print(f"  [Demucs] готово за {time.time() - start:.1f} с")
    if not out_path.exists():
        candidates = sorted(
            SEPARATED_DIR.rglob("vocals.wav"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            candidates[0].replace(out_path)
    if not out_path.exists():
        raise RuntimeError("Demucs не создал vocals.wav")
    return out_path


def transcribe(model, audio_path: str) -> tuple[str, str, float]:
    start = time.time()
    result = model.transcribe(
        audio_path,
        language=None,
        fp16=False,
        condition_on_previous_text=False,
        temperature=0.0,
    )
    return result["text"].strip(), result.get("language", ""), time.time() - start


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=MODELS)
    parser.add_argument("--tracks", nargs="+", default=list(TRACKS))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--output", default=str(RESULTS_DIR / "results.json"))
    args = parser.parse_args()

    SEPARATED_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    tracks = {name: TRACKS[name] for name in args.tracks}
    for name, config in tracks.items():
        if not config["audio"].exists():
            raise SystemExit(f"Нет аудиофайла: {config['audio']}")
        if not config["reference"].exists():
            raise SystemExit(f"Нет эталона: {config['reference']}")

    print("=" * 72)
    print("ЭТАП 1. Отделение вокала через Demucs")
    print("=" * 72)
    separated_paths = {}
    for name, config in tracks.items():
        print(f"\nТрек: {name}")
        separated_paths[name] = separate_vocals(
            config["audio"], name, force=args.force
        )

    references = {
        name: normalize(config["reference"].read_text(encoding="utf-8"))
        for name, config in tracks.items()
    }

    print("\n" + "=" * 72)
    print("ЭТАП 2. Распознавание речи")
    print("=" * 72)
    results = []
    for model_size in args.models:
        print(f"\n--- Whisper {model_size} ---")
        model = whisper.load_model(model_size)
        for name, config in tracks.items():
            for condition in CONDITIONS:
                audio_path = (
                    str(config["audio"])
                    if condition == "mix"
                    else str(separated_paths[name])
                )
                print(f"  [{name} | {condition} | {model_size}]", end=" ")
                text, language, elapsed = transcribe(model, audio_path)
                print(f"lang={language}, time={elapsed:.1f}s")
                (RESULTS_DIR / f"{name}__{condition}__{model_size}.txt").write_text(
                    text, encoding="utf-8"
                )
                hypothesis = normalize(text)
                reference = references[name]
                results.append(
                    {
                        "track": name,
                        "condition": condition,
                        "model": model_size,
                        "language": language,
                        "time_sec": round(elapsed, 1),
                        "wer": round(jiwer.wer(reference, hypothesis), 4),
                        "cer": round(jiwer.cer(reference, hypothesis), 4),
                    }
                )
        del model

    print("\n" + "=" * 72)
    print("РЕЗУЛЬТАТЫ")
    print("=" * 72)
    header = (
        f"{'Трек':<16} {'Условие':<9} {'Модель':<8} "
        f"{'WER':>8} {'CER':>8} {'Время, с':>10}"
    )
    print(header)
    print("-" * len(header))
    for result in results:
        print(
            f"{result['track']:<16} {result['condition']:<9} "
            f"{result['model']:<8} {result['wer']:>8.4f} "
            f"{result['cer']:>8.4f} {result['time_sec']:>10.1f}"
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nРезультаты сохранены: {output}")


if __name__ == "__main__":
    main()
