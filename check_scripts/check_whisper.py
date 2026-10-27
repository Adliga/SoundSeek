"""Проверка Whisper на первом треке."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import whisper

from check_scripts._common import first_audio


def main() -> None:
    source = first_audio()
    start = time.time()
    model = whisper.load_model("base")
    print(f"Модель загружена за {time.time() - start:.1f} с")
    start = time.time()
    result = model.transcribe(
        str(source),
        language=None,
        fp16=False,
        condition_on_previous_text=False,
        temperature=0.0,
    )
    print(f"Распознавание: {time.time() - start:.1f} с")
    print(f"Язык: {result.get('language')}")
    print(result.get("text", "").strip()[:1500])


if __name__ == "__main__":
    main()
