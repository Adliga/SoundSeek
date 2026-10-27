"""Проверка поиска по аудиофрагменту."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import librosa
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_scripts._common import first_audio, make_searcher


def make_fragment(source: Path, output: Path, seconds: float = 8.0) -> None:
    duration = librosa.get_duration(path=str(source))
    start = max(0.0, (duration - seconds) / 2)
    audio, _ = librosa.load(
        str(source), sr=48000, offset=start, duration=seconds, mono=True
    )
    sf.write(output, audio, 48000)


def main() -> None:
    source = first_audio()
    with tempfile.TemporaryDirectory() as tmp:
        fragment = Path(tmp) / "fragment.wav"
        make_fragment(source, fragment)
        searcher = make_searcher()
        print(f"Источник: {source.name}")
        for index, hit in enumerate(searcher.search_by_audio(fragment, top_k=5), 1):
            print(
                f"{index}. {hit.track.display_title} | "
                f"итог={hit.final_score:.3f} | {hit.explanations[0]}"
            )


if __name__ == "__main__":
    main()
