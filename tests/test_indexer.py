import os
from pathlib import Path

import numpy as np
import soundfile as sf

from soundseek_core.classifier import Classification
from soundseek_core.indexer import AudioIndexer, stable_track_id


class FakeAudioEmbedder:
    def embed_audio(self, audio, segments=3):
        vector = np.zeros(512, dtype="float32")
        vector[0] = 1.0
        return vector


class FakeTextEmbedder:
    def encode(self, text, is_query=False):
        vector = np.zeros(384, dtype="float32")
        vector[0] = 1.0
        return vector


class FakeClassifier:
    def classify(self, audio_emb, ontology=None, duration=0.0, tag_genre="", filename=""):
        return Classification(
            content_type="music",
            content_type_confidence=0.9,
            genre="rock",
            genre_source="test",
            genre_confidence=0.8,
            mood="happy",
            mood_confidence=0.7,
            has_vocal=True,
        )


def _write_wav(path: Path, frequency: float = 440.0, seconds: float = 2.0):
    sample_rate = 48_000
    time = np.arange(int(sample_rate * seconds)) / sample_rate
    data = 0.1 * np.sin(2 * np.pi * frequency * time).astype("float32")
    sf.write(path, data, sample_rate)


def test_stable_id_is_deterministic():
    one = stable_track_id("album/track.mp3")
    two = stable_track_id("album\\track.mp3")
    assert one == two
    assert one != stable_track_id("track.mp3")


def test_incremental_sync_add_skip_update_remove(tmp_path):
    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()
    wav = tracks_dir / "song.wav"
    _write_wav(wav)

    indexer = AudioIndexer(
        db_path=tmp_path / "indexes" / "library",
        load_models=False,
    )
    indexer._audio_embedder = FakeAudioEmbedder()
    indexer._text_embedder = FakeTextEmbedder()
    indexer._classifier = FakeClassifier()

    first = indexer.sync_folder(tracks_dir)
    assert first.added == 1
    assert len(indexer.db) == 1
    track = indexer.db.snapshot()[0]
    assert track.id == stable_track_id("song.wav")
    assert track.derived.genre == "rock"

    second = indexer.sync_folder(tracks_dir)
    assert second.skipped == 1
    assert len(indexer.db) == 1

    # Заставляем систему увидеть изменение файла.
    future = wav.stat().st_mtime + 10
    os.utime(wav, (future, future))
    third = indexer.sync_folder(tracks_dir)
    assert third.updated == 1

    wav.unlink()
    fourth = indexer.sync_folder(tracks_dir)
    assert fourth.removed == 1
    assert len(indexer.db) == 0


def test_force_reindex_preserves_manual_notes(tmp_path):
    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()
    wav = tracks_dir / "song.wav"
    _write_wav(wav, 330.0)

    indexer = AudioIndexer(db_path=tmp_path / "library", load_models=False)
    indexer._audio_embedder = FakeAudioEmbedder()
    indexer._text_embedder = FakeTextEmbedder()
    indexer._classifier = FakeClassifier()
    indexer.sync_folder(tracks_dir)

    track = indexer.db.snapshot()[0]
    indexer.update_track_fields(track.id, user_notes="важная пометка")
    indexer.sync_folder(tracks_dir, force=True)
    assert indexer.db.snapshot()[0].derived.user_notes == "важная пометка"


def test_force_reindex_preserves_manual_metadata(tmp_path):
    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()
    wav = tracks_dir / "song.wav"
    _write_wav(wav, 220.0)

    indexer = AudioIndexer(db_path=tmp_path / "library", load_models=False)
    indexer._audio_embedder = FakeAudioEmbedder()
    indexer._text_embedder = FakeTextEmbedder()
    indexer._classifier = FakeClassifier()
    indexer.sync_folder(tracks_dir)

    track = indexer.db.snapshot()[0]
    indexer.update_track_fields(
        track.id,
        title="Ручное название",
        artist="Ручной исполнитель",
        album="Ручной альбом",
        year=1999,
        tag_genre="Punk;Rock",
        derived_genre="punk_rock",
        derived_mood="rebellious",
    )
    indexer.sync_folder(tracks_dir, force=True)
    restored = indexer.db.snapshot()[0]
    assert restored.tags.title == "Ручное название"
    assert restored.tags.artist == "Ручной исполнитель"
    assert restored.tags.album == "Ручной альбом"
    assert restored.tags.year == 1999
    assert restored.tags.genre == "Punk;Rock"
    assert restored.derived.genre == "punk_rock"
    assert restored.derived.mood == "rebellious"


def test_title_mood_hint_overrides_unreliable_clap_mood(tmp_path):
    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()
    _write_wav(tracks_dir / "Lonely Day.wav", 220.0)
    indexer = AudioIndexer(db_path=tmp_path / "library", load_models=False)
    indexer._audio_embedder = FakeAudioEmbedder()
    indexer._text_embedder = FakeTextEmbedder()
    indexer._classifier = FakeClassifier()
    indexer.sync_folder(tracks_dir)
    track = indexer.db.snapshot()[0]
    assert track.derived.mood == "lonely"
    assert track.derived.confidences.get("mood_title_hint") == "lonely"
