"""Оркестратор гибридного поиска."""

from __future__ import annotations

from ..audio import load_query_audio
from ..config import CANDIDATE_MULTIPLIER, DEFAULT_TOP_K, MIN_RESULT_SCORE
from ..indexer import AudioIndexer
from ..models import ParsedQuery, SearchHit
from ..ontology import Ontology
from ..query_parser import parse_query
from ..rules import RuleEngine, tokenize
from . import fusion, lyrics, melody, metadata, semantic


class SearchEngine:
    def __init__(self, indexer: AudioIndexer, ontology: Ontology | None = None):
        self.indexer = indexer
        self.db = indexer.db
        self.ontology = ontology or indexer.ontology
        self.rules = RuleEngine(self.ontology)

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[SearchHit]:
        query = (query or "").strip()
        if not query:
            return []
        parsed = parse_query(query, self.ontology)
        if (
            not tokenize(parsed.free_text or parsed.raw)
            and not parsed.genres
            and not parsed.moods
            and not parsed.negated_genres
            and not parsed.negated_moods
            and parsed.has_vocal is None
            and parsed.year_from is None
            and parsed.artist == ""
        ):
            return []
        tracks = self.db.snapshot()

        channels: dict[str, list[tuple]] = {}
        meta_results = metadata.search_metadata(
            tracks, parsed, top_k=max(top_k * CANDIDATE_MULTIPLIER, 40)
        )
        if meta_results:
            channels["metadata"] = meta_results

        # Запросы вида «90-е», «без вокала», «не панк» не имеют текстового
        # ядра, поэтому одних метаданных/CLAP недостаточно: нужен канал
        # структурированных кандидатов, который затем отфильтруют правила.
        if (
            parsed.year_from is not None
            or parsed.year_to is not None
            or parsed.has_vocal is not None
            or parsed.negated_genres
            or parsed.negated_moods
        ):
            # Структурированный фильтр нужен и вместе с жанром/настроением:
            # иначе запрос «90-е панк» зависел бы от того, вернул ли CLAP
            # хоть одного кандидата.
            channels["filter"] = [(track, 1.0) for track in tracks]

        clap_results = semantic.search_text(
            self.db,
            self.indexer,
            parsed,
            top_k=max(top_k * CANDIDATE_MULTIPLIER, 40),
        )
        if clap_results:
            channels["clap"] = clap_results

        lyrics_results = lyrics.search_lyrics(
            self.db, parsed, lambda: self.indexer.text_embedder, top_k=30
        )
        if lyrics_results:
            channels["lyrics"] = lyrics_results

        if not channels:
            return []

        candidates = fusion.fuse(channels)
        ranked = self.rules.apply(parsed, candidates)
        results: list[SearchHit] = []
        for hit in ranked:
            if hit.final_score < MIN_RESULT_SCORE:
                continue
            self._add_channel_explanations(hit)
            results.append(hit)
            if len(results) >= top_k:
                break
        # Если найден явный лидер (например, точное название), не
        # показываем слабый CLAP-шум в качестве альтернатив.
        if len(results) > 1 and results[0].final_score >= 0.45:
            cutoff = max(MIN_RESULT_SCORE, results[0].final_score * 0.45)
            results = [hit for hit in results if hit.final_score >= cutoff]
        return results

    def search_by_audio(self, audio_input, top_k: int = DEFAULT_TOP_K) -> list[SearchHit]:
        """Поиск по фрагменту или напеванию: CLAP-тембр + мелодия."""
        audio = load_query_audio(audio_input)
        if audio.size == 0:
            return []
        parsed = ParsedQuery(raw="", free_text="", semantic_text="")
        tracks = self.db.snapshot()
        channels: dict[str, list[tuple]] = {}
        audio_results = semantic.search_audio(
            self.db,
            self.indexer,
            audio,
            top_k=max(top_k * CANDIDATE_MULTIPLIER, 40),
        )
        if audio_results:
            channels["audio"] = audio_results
        melody_results = melody.search_melody(
            tracks,
            audio,
            top_k=max(top_k * CANDIDATE_MULTIPLIER, 40),
        )
        if melody_results:
            channels["melody"] = melody_results
        if not channels:
            return []

        candidates = fusion.fuse(channels)
        ranked = self.rules.apply(parsed, candidates)
        results: list[SearchHit] = []
        for hit in ranked:
            if hit.final_score < MIN_RESULT_SCORE:
                continue
            details = []
            if "audio" in hit.channels:
                details.append(f"CLAP {hit.channels['audio']:.3f}")
            if "melody" in hit.channels:
                details.append(f"мелодия {hit.channels['melody']:.3f}")
            hit.explanations.insert(
                0,
                "поиск по звучанию: " + ", ".join(details),
            )
            results.append(hit)
            if len(results) >= top_k:
                break
        return results

    def search_by_humming(self, audio_input, top_k: int = DEFAULT_TOP_K) -> list[SearchHit]:
        """Совместимый псевдоним: напевание обрабатывается как аудиофрагмент."""
        return self.search_by_audio(audio_input, top_k=top_k)

    @staticmethod
    def _add_channel_explanations(hit: SearchHit) -> None:
        lines: list[str] = []
        if "metadata" in hit.channels:
            lines.append("канал метаданных: совпадение по названию/исполнителю")
        if "clap" in hit.channels:
            lines.append(
                f"CLAP: сходство описания {hit.channels['clap']:.3f}"
            )
        if "lyrics" in hit.channels:
            lines.append(
                f"канал текста песни: {hit.channels['lyrics']:.3f}"
            )
        if "filter" in hit.channels:
            lines.append("структурированный фильтр: год / вокал / отрицание")
        seen = set(hit.explanations)
        for line in lines:
            if line not in seen:
                hit.explanations.append(line)
                seen.add(line)
