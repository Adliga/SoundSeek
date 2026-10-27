import numpy as np

from soundseek_core.db import VectorDB
from tests.conftest import make_track


def _vector(index: int, dim: int = 8) -> np.ndarray:
    vector = np.zeros(dim, dtype="float32")
    vector[index] = 1.0
    return vector


def test_add_save_load_roundtrip(tmp_path):
    db = VectorDB(audio_dim=8, text_dim=8)
    track = make_track("a", title="A")
    db.add(_vector(0), track, _vector(0))
    db.save(tmp_path / "library")

    loaded = VectorDB()
    loaded.load(tmp_path / "library")
    assert len(loaded) == 1
    assert loaded.get("a").tags.title == "A"
    results = loaded.search_audio(_vector(0), 1)
    assert results[0][0].id == "a"


def test_remove_rebuilds_indexes():
    db = VectorDB(audio_dim=8, text_dim=8)
    db.add(_vector(0), make_track("a"), _vector(0))
    db.add(_vector(1), make_track("b"), _vector(1))
    removed = db.remove(["a"])
    assert removed == 1
    assert len(db) == 1
    results = db.search_audio(_vector(1), 2)
    assert results[0][0].id == "b"


def test_text_search_ignores_zero_vectors():
    db = VectorDB(audio_dim=8, text_dim=8)
    db.add(_vector(0), make_track("a"))
    db.add(_vector(1), make_track("b"), _vector(1))
    results = db.search_text(_vector(1), 5)
    assert [track.id for track, _ in results] == ["b"]


def test_reassign_ids():
    db = VectorDB(audio_dim=8, text_dim=8)
    db.add(_vector(0), make_track("old"))
    db.reassign_ids({"old": "new"})
    assert db.contains("new")
    assert not db.contains("old")
    assert db.get("new").id == "new"


def test_replace_keeps_vectors_in_sync():
    db = VectorDB(audio_dim=8, text_dim=8)
    db.add(_vector(0), make_track("a", title="Old"), _vector(0))
    updated = make_track("a", title="New")
    assert db.replace("a", _vector(1), updated, _vector(1)) is True
    assert len(db) == 1
    assert db.get("a").tags.title == "New"
    assert db.search_audio(_vector(1), 1)[0][0].id == "a"
    assert db.search_text(_vector(1), 1)[0][0].id == "a"
