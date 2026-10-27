"""Мелодический канал для поиска по напеванию.

Идея простая и воспроизводимая:

1. из аудио извлекается основной тон через ``librosa.pyin``;
2. контур переводится в MIDI-полутоны, сглаживается и приводится к
   сопоставимой длине;
3. запрос и трек сравниваются через DTW с subsequence-режимом: короткий
   напев может совпасть с фрагментом длинного трека.

Это не промышленный query-by-humming, но честный мелодический сигнал,
который не зависит от текстового описания и обучаемых классификаторов.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import median_filter

from .config import SAMPLE_RATE

MELODY_SAMPLE_RATE = 22_050
MELODY_POINTS = 96
MIN_MELODY_POINTS = 8


def _resample_sequence(values: np.ndarray, points: int) -> np.ndarray:
    if values.size == 0:
        return values.astype("float32")
    if values.size == 1:
        return np.full(points, float(values[0]), dtype="float32")
    source = np.linspace(0.0, 1.0, num=values.size)
    target = np.linspace(0.0, 1.0, num=points)
    return np.interp(target, source, values).astype("float32")


def extract_melody(
    audio: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
    max_seconds: int = 30,
    points: int = MELODY_POINTS,
) -> np.ndarray:
    """Возвращает нормализованный мелодический контур в полутонах."""
    import librosa

    if audio is None or np.asarray(audio).size == 0:
        return np.zeros(0, dtype="float32")
    y = np.asarray(audio, dtype="float32").reshape(-1)
    if sample_rate != MELODY_SAMPLE_RATE:
        y = librosa.resample(
            y, orig_sr=sample_rate, target_sr=MELODY_SAMPLE_RATE
        )
    max_samples = int(max_seconds * MELODY_SAMPLE_RATE)
    y = y[:max_samples]
    if y.size < MELODY_SAMPLE_RATE // 2:
        return np.zeros(0, dtype="float32")

    # Гармоническая составляющая уменьшает влияние ударных на pyin.
    y = librosa.effects.harmonic(y, margin=2.0)
    f0, voiced, _ = librosa.pyin(
        y,
        fmin=float(librosa.note_to_hz("C2")),
        fmax=float(librosa.note_to_hz("C6")),
        sr=MELODY_SAMPLE_RATE,
        frame_length=2048,
        hop_length=512,
        fill_na=np.nan,
    )
    midi = librosa.hz_to_midi(f0)
    valid = np.isfinite(midi)
    if valid.sum() < MIN_MELODY_POINTS:
        return np.zeros(0, dtype="float32")

    indices = np.arange(midi.size)
    midi = np.interp(indices, indices[valid], midi[valid])
    midi = median_filter(midi, size=5, mode="nearest")
    midi = _resample_sequence(midi, points)
    # Убираем абсолютную высоту: для напевания важнее интервалы и контур,
    # а не точная тональность.
    midi = midi - float(np.median(midi))
    return midi.astype("float32")



def extract_chroma(
    audio: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
    max_seconds: int = 30,
) -> np.ndarray:
    """CENS-хрома для устойчивого сравнения гармонии и напева."""
    import librosa

    if audio is None or np.asarray(audio).size == 0:
        return np.zeros((12, 0), dtype="float32")
    y = np.asarray(audio, dtype="float32").reshape(-1)
    if sample_rate != MELODY_SAMPLE_RATE:
        y = librosa.resample(y, orig_sr=sample_rate, target_sr=MELODY_SAMPLE_RATE)
    y = y[: int(max_seconds * MELODY_SAMPLE_RATE)]
    if y.size < MELODY_SAMPLE_RATE // 2:
        return np.zeros((12, 0), dtype="float32")
    return librosa.feature.chroma_cens(
        y=y,
        sr=MELODY_SAMPLE_RATE,
        hop_length=512,
        n_chroma=12,
    ).astype("float32")


def chroma_similarity(
    query: np.ndarray,
    track: np.ndarray,
    *,
    min_frames: int = 8,
) -> float:
    import librosa

    query = np.asarray(query, dtype="float32")
    track = np.asarray(track, dtype="float32")
    if query.ndim != 2 or track.ndim != 2:
        return 0.0
    if query.shape[1] < min_frames or track.shape[1] < min_frames:
        return 0.0
    short, long = (query, track) if query.shape[1] <= track.shape[1] else (track, query)
    try:
        cost, path = librosa.sequence.dtw(
            X=short,
            Y=long,
            subseq=True,
            metric="cosine",
        )
    except Exception:
        return 0.0
    if path is None or len(path) == 0:
        return 0.0
    mean_cost = float(cost[-1, :].min()) / max(1, len(path))
    return float(np.exp(-mean_cost / 0.04))

def melody_similarity(
    query: np.ndarray,
    track: np.ndarray,
    *,
    min_points: int = MIN_MELODY_POINTS,
) -> float:
    """Сходство двух мелодических контуров в диапазоне 0..1."""
    import librosa

    query = np.asarray(query, dtype="float32").reshape(-1)
    track = np.asarray(track, dtype="float32").reshape(-1)
    if query.size < min_points or track.size < min_points:
        return 0.0

    # DTW требует, чтобы X был короче Y при subseq=True.
    short, long = (query, track) if query.size <= track.size else (track, query)
    try:
        cost, path = librosa.sequence.dtw(
            X=short[np.newaxis, :],
            Y=long[np.newaxis, :],
            subseq=True,
            metric="euclidean",
        )
    except Exception:
        return 0.0
    if path is None or len(path) == 0:
        return 0.0
    mean_cost = float(cost[-1, :].min()) / max(1, len(path))
    # Среднее расхождение в полутонах; 2.5 — эмпирическая шкала,
    # откалиброванная на синтетических и реальных контурах.
    return float(np.exp(-mean_cost / 2.5))
