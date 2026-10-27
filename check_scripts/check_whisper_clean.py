"""Проверка Whisper на отделённой вокальной дорожке."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import whisper

from check_scripts._common import SEPARATED_DIR

EXPERIMENTS_SEPARATED = (
    Path(__file__).resolve().parent.parent / "experiments" / "separated"
)


def main() -> None:
    candidates = sorted(SEPARATED_DIR.rglob("vocals.wav")) + sorted(
        EXPERIMENTS_SEPARATED.rglob("vocals.wav")
    )
    if not candidates:
        raise SystemExit(
            "Нет vocals.wav. Сначала запустите check_scripts/check_demucs.py."
        )
    source = candidates[0]
    model = whisper.load_model("base")
    start = time.time()
    result = model.transcribe(
        str(source),
        language=None,
        fp16=False,
        condition_on_previous_text=False,
        temperature=0.0,
    )
    print(f"Файл: {source}")
    print(f"Время: {time.time() - start:.1f} с")
    print(f"Язык: {result.get('language')}")
    print(result.get("text", "").strip()[:1500])


if __name__ == "__main__":
    main()
