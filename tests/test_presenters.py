from __future__ import annotations

from soundseek_core.models import SearchHit
from tests.conftest import make_track
from web_app.presenters import format_results


def test_result_card_uses_dark_theme_markup() -> None:
    track = make_track(
        "miku",
        "Ms. Miku After Dark",
        "Astrophysics",
        "j_pop",
        "dark",
        lyrics="sample lyric",
        tag_genre="J-Pop",
    )
    track.derived.genre_source = "clap"
    track.derived.user_notes = "любимое"
    hit = SearchHit(
        track=track,
        base_score=0.8,
        final_score=0.9,
        explanations=["совпадение по метаданным"],
        channels={"clap": 0.4, "notes": 1.0},
    )

    html = format_results([hit], "текст запроса: miku")

    assert 'class="soundseek-result-card"' in html
    assert "soundseek-summary" in html
    assert "soundseek-result-meta" in html
    assert "soundseek-score-detail" in html
    assert 'data-track-play="miku"' in html
    assert "Заметка" in html


def test_empty_result_uses_empty_card_class() -> None:
    html = format_results([], empty_hint="Ничего не найдено.")

    assert "soundseek-empty-card" in html
    assert "Ничего не найдено." in html
