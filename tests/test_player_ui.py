from __future__ import annotations

from tests.conftest import make_track
from web_app.player_ui import (
    PLAY_BUTTON_JS,
    format_player_meta,
    play_button_html,
)


def test_play_button_escapes_track_id_and_title() -> None:
    html = play_button_html('a"b', "Title <track>")

    assert 'data-track-play="a&quot;b"' in html
    assert "Воспроизвести Title &lt;track&gt;" in html
    assert "soundseek-play-button" in html
    assert "Title <track>" not in html


def test_empty_track_id_has_no_play_button() -> None:
    assert play_button_html("") == ""


def test_player_meta_contains_track_context() -> None:
    track = make_track(
        "track-1",
        "Track <One>",
        "Artist & Co",
        "rock",
        "calm",
        album="Record",
    )

    html = format_player_meta(track)

    assert "soundseek-player-track" in html
    assert "Track &lt;One&gt;" in html
    assert "Artist &amp; Co" in html
    assert "Record" in html
    assert "rock" in html
    assert "calm" in html


def test_play_js_triggers_single_global_event() -> None:
    assert "track_play" in PLAY_BUTTON_JS
    assert "data-track-play" in PLAY_BUTTON_JS
    assert "trigger(" in PLAY_BUTTON_JS
