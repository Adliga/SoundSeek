"""Загрузка аудио и детерминированная нарезка окон."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import librosa
import numpy as np

from .config import (
    CLAP_WINDOW_SECONDS,
    INDEX_MAX_WINDOWS,
    INDEX_WINDOW_SECONDS,
    QUERY_WINDOW_SECONDS,
    SAMPLE_RATE,
)


def peak_normalize(audio: np.ndarray) -> np.ndarray:
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1e-6:
        audio = audio / peak * 0.95
    return audio.astype("float32", copy=False)


def load_middle(path: str | Path, seconds: int = QUERY_WINDOW_SECONDS) -> np.ndarray:
    """Берёт детерминированный фрагмент из середины трека."""
    duration = float(librosa.get_duration(path=str(path)))
    if duration > seconds:
        start = max(0.0, (duration - seconds) / 2.0)
        audio, _ = librosa.load(
            str(path),
            sr=SAMPLE_RATE,
            offset=start,
            duration=seconds,
            mono=True,
        )
    else:
        audio, _ = librosa.load(str(path), sr=SAMPLE_RATE, mono=True)
    return peak_normalize(audio)


def load_track_audio(path: str | Path) -> np.ndarray:
    """Загружает трек целиком для CLAP-индексации.

    CLAP не принимает произвольную длину как один пример, поэтому дальше
    трек детерминированно делится на 10-секундные окна по всей длительности.
    """
    audio, _ = librosa.load(str(path), sr=SAMPLE_RATE, mono=True)
    return peak_normalize(audio)


def middle_segment(
    audio: np.ndarray,
    seconds: int = INDEX_WINDOW_SECONDS,
) -> np.ndarray:
    """Возвращает средний фрагмент уже загруженного аудио."""
    audio = np.asarray(audio, dtype="float32").reshape(-1)
    size = int(seconds * SAMPLE_RATE)
    if audio.size <= size:
        return audio
    start = max(0, (audio.size - size) // 2)
    return audio[start : start + size]


def index_window_count(
    duration: float,
    window_seconds: int = CLAP_WINDOW_SECONDS,
    max_windows: int = INDEX_MAX_WINDOWS,
) -> int:
    """Считает число 10-секундных окон для покрытия всего трека.

    ``ceil`` гарантирует, что последний фрагмент трека тоже попадёт в
    индекс. Для очень длинных файлов число окон ограничивается, чтобы
    индексация оставалась предсказуемой по времени.
    """
    if duration <= 0:
        return 1
    count = max(1, int(math.ceil(duration / float(window_seconds))))
    if max_windows > 0:
        count = min(count, max_windows)
    return count


def load_query_audio(source: Any, max_seconds: int = QUERY_WINDOW_SECONDS) -> np.ndarray:
    """Загружает аудиозапрос из пути, file-like объекта или numpy-массива.

    Для numpy-массива предполагается, что он уже приведён к SAMPLE_RATE.
    """
    if source is None:
        raise ValueError("Пустой аудиозапрос")

    if isinstance(source, tuple) and len(source) == 2:
        # Некоторые клиенты Gradio и звуковых библиотек отдают пару
        # (sample_rate, samples). Приводим её к единому sample rate.
        sample_rate, samples = source
        if isinstance(samples, np.ndarray):
            audio = np.asarray(samples, dtype="float32").reshape(-1)
            if int(sample_rate) != SAMPLE_RATE:
                audio = librosa.resample(
                    audio, orig_sr=int(sample_rate), target_sr=SAMPLE_RATE
                )
            return peak_normalize(audio[: max_seconds * SAMPLE_RATE])

    if isinstance(source, np.ndarray):
        audio = np.asarray(source, dtype="float32").reshape(-1)
        return peak_normalize(audio[: max_seconds * SAMPLE_RATE])

    if isinstance(source, (str, Path)):
        return load_middle(source, seconds=max_seconds)

    if hasattr(source, "read"):
        # Gradio обычно отдаёт путь, но на всякий случай поддерживаем file-like.
        audio, _ = librosa.load(source, sr=SAMPLE_RATE, mono=True, duration=max_seconds)
        return peak_normalize(audio)

    raise TypeError(f"Неподдерживаемый тип аудиовхода: {type(source)!r}")


def split_into_windows(
    audio: np.ndarray,
    window_seconds: int,
    segments: int,
) -> list[np.ndarray]:
    """Делит аудио на ``segments`` фиксированных окон.

    Окна выбираются детерминированно: начало, середина и конец доступного
    фрагмента. Это устраняет случайность ``rand_trunc`` в CLAP.
    """
    window_size = int(window_seconds * SAMPLE_RATE)
    if audio.size <= window_size:
        return [audio]
    segments = max(1, segments)
    if segments == 1:
        start = max(0, (audio.size - window_size) // 2)
        return [audio[start : start + window_size]]
    if segments == 2:
        starts = [0, audio.size - window_size]
    else:
        max_start = audio.size - window_size
        starts = [
            round(i * max_start / (segments - 1))
            for i in range(segments)
        ]
        starts = sorted(set(starts))
    return [audio[start : start + window_size] for start in starts]
