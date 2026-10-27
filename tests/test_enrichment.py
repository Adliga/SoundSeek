import numpy as np

from soundseek_core.enrichment import EnrichmentService

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


def test_force_enrichment_keeps_previous_lyrics_on_empty_asr(monkeypatch):
    track = make_track("song", lyrics="Старый сохранённый текст", has_vocal=True)
    track.derived.enrich_status = "done"
    service, db = _service()
    monkeypatch.setattr(service, "_separate_vocals", lambda path, tmp: "vocals.wav")
    monkeypatch.setattr(service, "_transcribe", lambda path: ("", "", [], ""))

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
        lambda path: (
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
