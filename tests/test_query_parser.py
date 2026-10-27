from soundseek_core.ontology import Ontology
from soundseek_core.query_parser import parse_query


def test_negation_rock_but_not_punk(ontology: Ontology):
    query = parse_query("рок, но не панк", ontology)
    assert query.genres == ["rock"]
    assert query.negated_genres == ["punk_rock"]


def test_happy_punk(ontology: Ontology):
    query = parse_query("весёлый панк", ontology)
    assert query.genres == ["punk_rock"]
    assert query.moods == ["happy"]


def test_no_vocal(ontology: Ontology):
    query = parse_query("спокойное без вокала", ontology)
    assert query.has_vocal is False
    assert any(mood in {"calm", "peaceful", "relaxing"} for mood in query.moods)


def test_instrumental(ontology: Ontology):
    query = parse_query("instrumental piano", ontology)
    assert query.has_vocal is False


def test_decade(ontology: Ontology):
    query = parse_query("рок 90-х", ontology)
    assert query.year_from == 1990
    assert query.year_to == 1999


def test_years(ontology: Ontology):
    query = parse_query("rock 1994 1998", ontology)
    assert query.year_from == 1994
    assert query.year_to == 1998


def test_artist_quotes(ontology: Ontology):
    query = parse_query('грустный "System Of A Down"', ontology)
    assert query.artist == "System Of A Down"


def test_semantic_text_uses_ontology(ontology: Ontology):
    query = parse_query("весёлый панк", ontology)
    assert "punk" in query.semantic_text.lower()
    assert "happy" in query.semantic_text.lower()


def test_parse_decade_spellings(ontology: Ontology):
    for raw in ("90-е", "90-х", "90s", "девяностые"):
        query = parse_query(raw, ontology)
        assert (query.year_from, query.year_to) == (1990, 1999), raw
    query = parse_query("2010-е", ontology)
    assert (query.year_from, query.year_to) == (2010, 2019)


def test_negated_instrumental_means_vocal(ontology: Ontology):
    assert parse_query("не инструментал", ontology).has_vocal is True
    assert parse_query("без инструментала", ontology).has_vocal is True
    assert parse_query("без вокала", ontology).has_vocal is False
    assert parse_query("не вокал", ontology).has_vocal is False

def test_english_vocal_negation(ontology: Ontology):
    assert parse_query("without vocals", ontology).has_vocal is False
    assert parse_query("not vocals", ontology).has_vocal is False
    assert parse_query("no vocals", ontology).has_vocal is False
    assert parse_query("not instrumental", ontology).has_vocal is True
    assert parse_query("no instrumental", ontology).has_vocal is True
