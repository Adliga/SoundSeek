from __future__ import annotations

import numpy as np
import pytest

from soundseek_core.models import DerivedData, FileTags, Track
from soundseek_core.ontology import Ontology


@pytest.fixture(scope="session")
def ontology() -> Ontology:
    return Ontology()


def make_track(
    track_id: str,
    title: str = "",
    artist: str = "",
    genre: str = "",
    mood: str = "",
    *,
    tag_genre: str = "",
    content_type: str = "music",
    has_vocal: bool | None = True,
    lyrics: str = "",
    year: int | None = None,
    path: str | None = None,
    album: str = "",
    album_artist: str = "",
    cover_path: str = "",
    track_number: int | None = None,
) -> Track:
    return Track(
        id=track_id,
        path=path or f"data/tracks/{track_id}.mp3",
        tags=FileTags(
            title=title,
            artist=artist,
            album=album,
            album_artist=album_artist,
            cover_path=cover_path,
            track_number=track_number,
            genre=tag_genre,
            year=year,
        ),
        derived=DerivedData(
            content_type=content_type,
            genre=genre,
            mood=mood,
            has_vocal=has_vocal,
            lyrics=lyrics,
            duration=180.0,
        ),
    )


@pytest.fixture
def tracks() -> list[Track]:
    return [
        make_track("lonely_day", "Lonely Day", "System Of A Down", "alternative_metal", "sad"),
        make_track("punk1", "Punk One", "Punk Band", "punk_rock", "energetic", tag_genre="Punk;Rock"),
        make_track("metal1", "Metal One", "Metal Band", "heavy_metal", "aggressive"),
        make_track("pop1", "Pop One", "Pop Artist", "j_pop", "happy"),
        make_track("speech1", "Lecture", "Speaker", "", "", content_type="speech"),
    ]


@pytest.fixture
def unit_vector() -> np.ndarray:
    vector = np.zeros(512, dtype="float32")
    vector[0] = 1.0
    return vector
