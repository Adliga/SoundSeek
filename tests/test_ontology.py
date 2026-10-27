from soundseek_core.ontology import Ontology, normalize_text, stem_word


def test_trap_does_not_contain_rap(ontology: Ontology):
    concepts = ontology.extract_concepts("trap")
    assert concepts["genres"] == ["trap"]


def test_synthpop_does_not_contain_pop(ontology: Ontology):
    concepts = ontology.extract_concepts("synthpop")
    assert concepts["genres"] == ["synthpop"]


def test_pop_punk_is_one_phrase(ontology: Ontology):
    concepts = ontology.extract_concepts("pop punk")
    assert concepts["genres"] == ["pop_punk"]


def test_k_pop_phrase(ontology: Ontology):
    concepts = ontology.extract_concepts("k-pop")
    assert concepts["genres"] == ["k_pop"]


def test_russian_morphology(ontology: Ontology):
    assert "punk_rock" in ontology.extract_concepts("панка")["genres"]
    assert "sad" in ontology.extract_concepts("грустного")["moods"]


def test_genre_distance_and_within(ontology: Ontology):
    assert ontology.genre_distance("punk_rock", "pop_punk") == 1
    assert ontology.genre_distance("punk_rock", "heavy_metal") == 2
    assert ontology.is_genre_related("punk_rock", "heavy_metal")
    assert ontology.is_genre_within("pop_punk", "punk_rock")
    assert not ontology.is_genre_within("heavy_metal", "punk_rock")


def test_map_genre_value_uses_specific_genre(ontology: Ontology):
    assert ontology.map_genre_value("Punk;Rock") == "punk_rock"
    assert ontology.map_genre_value("Rock/Pop") in {"rock", "pop"}
    assert ontology.map_genre_value("Heavy Metal") == "heavy_metal"
    assert ontology.map_genre_value("unknown-tag") == ""


def test_normalize_and_stem():
    assert normalize_text("Ёлка_и-рок") == "елка и рок"
    assert stem_word("грустного") == "грустн"
