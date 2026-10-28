from __future__ import annotations

import numpy as np

from soundseek_core.visualization import build_embedding_map
from tests.conftest import make_track
from web_app.map_ui import MAP_JS


class FakeDB:
    def __init__(self, tracks):
        self._tracks = tracks

    def snapshot(self):
        return self._tracks

    def audio_matrix(self):
        return np.eye(len(self._tracks), 512, dtype="float32")


def test_embedding_map_keeps_legend_outside_svg() -> None:
    tracks = [
        make_track("a", "A <track>", 'Artist "A"', "rock", "calm"),
        make_track("b", "B", "Artist B", "rock", "happy"),
        make_track("c", "C", "Artist C", "pop", "calm"),
    ]

    html = build_embedding_map(FakeDB(tracks), color_by="genre")

    assert "soundseek-map-card" in html
    assert html.count("data-track-id=") == 3
    assert 'data-track-id="a"' in html
    assert "A &lt;track&gt;" in html
    assert "soundseek-map-legend-block" in html
    assert html.index("soundseek-map-legend-block") > html.index("</svg>")
    assert "2" in html  # количество треков в категории rock


def test_map_js_triggers_track_click_and_marks_selection() -> None:
    assert "track_click" in MAP_JS
    assert "selected" in MAP_JS
    assert "soundseek-map-tooltip" in MAP_JS
