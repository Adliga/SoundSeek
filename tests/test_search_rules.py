from soundseek_core.models import ParsedQuery
from soundseek_core.ontology import Ontology
from soundseek_core.query_parser import parse_query
from soundseek_core.rules import RuleEngine
from soundseek_core.search import fusion, metadata
from tests.conftest import make_track


def test_metadata_exact_title(ontology: Ontology, tracks):
    query = parse_query("lonely day", ontology)
    results = metadata.search_metadata(tracks, query)
    assert results
    assert results[0][0].id == "lonely_day"
    assert results[0][1] == 1.0


def test_metadata_does_not_use_path():
    track = make_track(
        "noise",
        title="Track",
        artist="Artist",
        genre="pop",
        path="C:/Music Video/Official Audio/track.mp3",
    )
    query = ParsedQuery(raw="music", free_text="music")
    assert metadata.score_track(track, query) == 0.0


def test_metadata_multi_token_requires_two_matches(ontology: Ontology):
    tracks = [
        make_track("down", title="Down", artist="Other"),
        make_track("soad", title="Cigaro", artist="System Of A Down"),
    ]
    query = parse_query("system of a down", ontology)
    results = metadata.search_metadata(tracks, query)
    assert results[0][0].id == "soad"


def test_genre_rule_uses_normalized_genre(ontology: Ontology):
    track = make_track(
        "punk",
        title="Punk",
        genre="punk_rock",
        mood="energetic",
        tag_genre="Punk;Rock",
    )
    engine = RuleEngine(ontology)
    query = parse_query("весёлый панк", ontology)
    hits = engine.apply(query, [(track, 0.5, {}, {})])
    assert hits
    assert any(hit.rule_name == "genre_match" for hit in hits[0].rule_hits)
    assert not any(hit.rule_name == "genre_conflict" for hit in hits[0].rule_hits)


def test_negated_punk_does_not_remove_metal(ontology: Ontology):
    track = make_track("metal", title="Metal", genre="heavy_metal", mood="aggressive")
    engine = RuleEngine(ontology)
    query = parse_query("рок, но не панк", ontology)
    hits = engine.apply(query, [(track, 0.5, {}, {})])
    assert len(hits) == 1


def test_negated_punk_removes_pop_punk(ontology: Ontology):
    track = make_track("pop_punk", title="Pop Punk", genre="pop_punk", mood="happy")
    engine = RuleEngine(ontology)
    query = parse_query("рок, но не панк", ontology)
    assert engine.apply(query, [(track, 0.5, {}, {})]) == []


def test_vocal_filter(ontology: Ontology):
    instrumental = make_track("i", genre="ambient", has_vocal=False)
    vocal = make_track("v", genre="pop", has_vocal=True)
    engine = RuleEngine(ontology)
    query = parse_query("без вокала", ontology)
    hits = engine.apply(query, [(instrumental, 0.5, {}, {}), (vocal, 0.5, {}, {})])
    assert [hit.track.id for hit in hits] == ["i"]


def test_fusion_prefers_multiple_channels():
    first = make_track("first", genre="rock")
    second = make_track("second", genre="rock")
    channels = {
        "metadata": [(first, 0.8)],
        "clap": [(first, 0.5), (second, 0.5)],
    }
    fused = fusion.fuse(channels)
    assert fused[0][0].id == "first"


def test_vocal_filter_excludes_unknown(ontology: Ontology):
    unknown = make_track("u", genre="ambient", has_vocal=None)
    instrumental = make_track("i", genre="ambient", has_vocal=False)
    engine = RuleEngine(ontology)
    query = parse_query("без вокала", ontology)
    hits = engine.apply(query, [(unknown, 0.5, {}, {}), (instrumental, 0.5, {}, {})])
    assert [hit.track.id for hit in hits] == ["i"]


def test_year_filter_requires_known_year(ontology: Ontology):
    known = make_track("known", genre="rock", year=1995)
    unknown = make_track("unknown", genre="rock", year=None)
    engine = RuleEngine(ontology)
    query = parse_query("90-е", ontology)
    hits = engine.apply(query, [(known, 0.5, {}, {}), (unknown, 0.5, {}, {})])
    assert [hit.track.id for hit in hits] == ["known"]


def test_negated_genre_excludes_speech(ontology: Ontology):
    speech = make_track("speech", content_type="speech")
    music = make_track("music", genre="heavy_metal")
    engine = RuleEngine(ontology)
    query = parse_query("не панк", ontology)
    hits = engine.apply(query, [(speech, 0.5, {}, {}), (music, 0.5, {}, {})])
    assert [hit.track.id for hit in hits] == ["music"]


def test_specific_genre_does_not_match_sibling(ontology: Ontology):
    assert ontology.genre_matches("hard_rock", "rock")
    assert ontology.genre_matches("rap", "trap")
    assert not ontology.genre_matches("indie_rock", "punk_rock")
    assert not ontology.genre_matches("heavy_metal", "punk_rock")


def test_hard_filter_removes_incompatible_known_genre(ontology: Ontology):
    indie = make_track("indie", genre="indie_rock", mood="happy")
    punk = make_track("punk", genre="punk_rock", mood="happy")
    engine = RuleEngine(ontology)
    hits = engine.apply(
        parse_query("весёлый панк", ontology),
        [(indie, 0.5, {}, {}), (punk, 0.5, {}, {})],
    )
    assert [hit.track.id for hit in hits] == ["punk"]


def test_mood_filter_removes_known_incompatible_mood(ontology: Ontology):
    sad = make_track("sad", genre="rock", mood="sad")
    happy = make_track("happy", genre="rock", mood="happy")
    unknown = make_track("unknown", genre="rock", mood="")
    engine = RuleEngine(ontology)
    hits = engine.apply(
        parse_query("грустный рок", ontology),
        [(sad, 0.5, {}, {}), (happy, 0.5, {}, {}), (unknown, 0.4, {}, {})],
    )
    assert {hit.track.id for hit in hits} == {"sad", "unknown"}

def test_mood_filter_keeps_exact_title_match(ontology: Ontology):
    track = make_track("lonely", title="Lonely Day", genre="rock", mood="happy")
    engine = RuleEngine(ontology)
    hits = engine.apply(parse_query("lonely day", ontology), [(track, 0.5, {}, {})])
    assert [hit.track.id for hit in hits] == ["lonely"]
