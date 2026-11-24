import numpy as np

from soundseek_core.config import WHISPER_MODEL_SIZE
from soundseek_core.enrichment import (
    EnrichmentService,
    _language_hint,
    _looks_like_hallucination,
)

from .conftest import make_track


class FakeDB:
    text_dim = 384

    def __init__(self):
        self.updated: list[tuple[str, np.ndarray]] = []

    def update_text(self, track_id: str, embedding: np.ndarray) -> None:
        self.updated.append((track_id, embedding))


class FakeTextEmbedder:
    def encode(self, text: str, is_query: bool = False) -> np.ndarray:
        return np.ones(384, dtype="float32")


def _service() -> tuple[EnrichmentService, FakeDB]:
    db = FakeDB()
    service = EnrichmentService(
        db=db,
        text_embedder=lambda: FakeTextEmbedder(),
        save_callback=lambda: None,
    )
    return service, db


def test_whisper_size_falls_back_when_none_is_passed():
    service = EnrichmentService(
        db=FakeDB(),
        text_embedder=lambda: FakeTextEmbedder(),
        save_callback=lambda: None,
        whisper_model_size=None,
    )
    assert service.whisper_model_size == WHISPER_MODEL_SIZE


def test_force_enrichment_keeps_previous_lyrics_on_empty_asr(monkeypatch):
    track = make_track("song", lyrics="Старый сохранённый текст", has_vocal=True)
    track.derived.enrich_status = "done"
    service, db = _service()
    monkeypatch.setattr(service, "_separate_vocals", lambda path, tmp: "vocals.wav")
    monkeypatch.setattr(
        service,
        "_transcribe",
        lambda path, language=None: ("", "", [], ""),
    )

    assert service.enrich_single_track(track, force=True) is True
    assert track.derived.lyrics == "Старый сохранённый текст"
    assert track.derived.has_vocal is True
    assert track.derived.enrich_status == "done"
    assert db.updated and db.updated[0][0] == "song"


def test_force_enrichment_replaces_lyrics_and_marks_whisper(monkeypatch):
    track = make_track("song", lyrics="", has_vocal=None)
    service, _ = _service()
    monkeypatch.setattr(service, "_separate_vocals", lambda path, tmp: "vocals.wav")
    monkeypatch.setattr(
        service,
        "_transcribe",
        lambda path, language=None: (
            "Новый распознанный текст песни",
            "ru",
            [],
            "",
        ),
    )

    assert service.enrich_single_track(track, force=True) is True
    assert track.derived.lyrics == "Новый распознанный текст песни"
    assert track.derived.lyrics_source == "whisper"
    assert track.derived.has_vocal is True


def test_language_hint_uses_cyrillic_metadata():
    track = make_track("track", "Бал лицемеров", "Порнофильмы")
    assert _language_hint(track) == "ru"


def test_language_hint_uses_japanese_metadata():
    track = make_track("track", "ギラギラ", "Ado")
    assert _language_hint(track) == "ja"


def test_hallucination_detector_catches_repeated_words():
    assert _looks_like_hallucination("мастер, " * 20)
    assert _looks_like_hallucination("Аааааааааааааааааа")
    assert not _looks_like_hallucination("Я управляю ритмами сердец")
