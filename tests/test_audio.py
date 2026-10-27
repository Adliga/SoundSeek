import numpy as np

from soundseek_core.audio import load_query_audio, peak_normalize, split_into_windows
from soundseek_core.config import SAMPLE_RATE


def test_peak_normalize_keeps_silence():
    audio = peak_normalize(np.zeros(100, dtype="float32"))
    assert audio.size == 100
    assert np.max(np.abs(audio)) == 0.0


def test_peak_normalize_scales_peak():
    audio = peak_normalize(np.array([0.0, 0.5, -1.0], dtype="float32"))
    assert np.isclose(np.max(np.abs(audio)), 0.95)


def test_load_query_audio_accepts_sample_rate_tuple():
    samples = np.ones(24000, dtype="float32")
    audio = load_query_audio((24000, samples), max_seconds=1)
    assert audio.dtype == np.float32
    assert audio.size == SAMPLE_RATE
    assert np.isclose(np.max(np.abs(audio)), 0.95)


def test_split_into_windows_is_deterministic():
    audio = np.arange(3 * SAMPLE_RATE, dtype="float32")
    windows = split_into_windows(audio, window_seconds=1, segments=3)
    assert len(windows) == 3
    assert all(window.size == SAMPLE_RATE for window in windows)
    assert [float(window[0]) for window in windows] == [
        0.0,
        float(SAMPLE_RATE),
        float(2 * SAMPLE_RATE),
    ]
