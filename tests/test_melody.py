import numpy as np

from soundseek_core.melody import (
    chroma_similarity,
    extract_chroma,
    extract_melody,
    melody_similarity,
)


def _tone(frequencies: list[float], seconds_per_note: float = 1.0) -> np.ndarray:
    sample_rate = 48_000
    parts = []
    for frequency in frequencies:
        time = np.arange(int(sample_rate * seconds_per_note)) / sample_rate
        parts.append(0.2 * np.sin(2 * np.pi * frequency * time))
    return np.concatenate(parts).astype("float32")


def test_melody_self_similarity():
    audio = _tone([220.0, 330.0, 440.0])
    contour = extract_melody(audio)
    assert contour.size > 8
    assert melody_similarity(contour, contour) > 0.99


def test_melody_is_transposition_invariant():
    low = extract_melody(_tone([220.0, 330.0, 440.0]))
    high = extract_melody(_tone([440.0, 660.0, 880.0]))
    assert melody_similarity(low, high) > 0.85


def test_chroma_similarity_self():
    audio = _tone([220.0, 330.0, 440.0])
    chroma = extract_chroma(audio)
    assert chroma.shape[0] == 12
    assert chroma_similarity(chroma, chroma) > 0.99


def test_chroma_differs_for_unrelated_audio():
    first = extract_chroma(_tone([220.0, 330.0, 440.0]))
    second = extract_chroma(_tone([110.0, 120.0, 130.0]))
    assert chroma_similarity(first, second) < 0.8
