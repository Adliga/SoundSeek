"""Классификация аудио: тип контента, жанр и настроение."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import torch
import torch.nn.functional as F

from .config import (
    CONFIDENCE_MARGIN,
    CONFIDENCE_THRESHOLD,
    LONG_FORM_THRESHOLD,
    MIN_MUSIC_DURATION,
)
from .embeddings import AudioEmbedder
from .ontology import Ontology


@dataclass
class PromptPrediction:
    label: str
    score: float
    margin: float
    scores: dict[str, float] = field(default_factory=dict)


@dataclass
class Classification:
    content_type: str = "unknown"
    content_type_confidence: float = 0.0
    genre: str = ""
    genre_source: str = ""
    genre_confidence: float = 0.0
    mood: str = ""
    mood_confidence: float = 0.0
    has_vocal: bool | None = None
    confidences: dict = field(default_factory=dict)
    genre_candidates: list[tuple[str, float]] = field(default_factory=list)


class PromptBank:
    """Кэширует текстовые эмбеддинги промптов.

    Раньше 69 текстов кодировались заново на каждый трек. Теперь — один раз
    на словарь промптов.
    """

    def __init__(self, embedder: AudioEmbedder):
        self.embedder = embedder
        self._cache: dict[tuple[tuple[str, str], ...], tuple[list[str], torch.Tensor]] = {}

    def get(self, prompts: dict[str, str]) -> tuple[list[str], torch.Tensor]:
        key = tuple(prompts.items())
        if key not in self._cache:
            self._cache[key] = self.embedder.embed_prompts(prompts)
        return self._cache[key]

    def predict(
        self,
        audio_emb: np.ndarray,
        prompts: dict[str, str],
        threshold: float = CONFIDENCE_THRESHOLD,
        require_margin: bool = True,
    ) -> PromptPrediction:
        if not prompts:
            return PromptPrediction("unknown", 0.0, 0.0, {})
        names, text_embs = self.get(prompts)
        audio_t = torch.tensor(audio_emb, dtype=torch.float32).reshape(1, -1)
        audio_t = F.normalize(audio_t, dim=-1)
        sims = (audio_t @ text_embs.T).reshape(-1)
        values, indices = torch.topk(sims, k=min(3, len(names)))
        scores = {names[i]: float(sims[i]) for i in range(len(names))}
        best_idx = int(indices[0])
        best_score = float(values[0])
        second = float(values[1]) if len(values) > 1 else 0.0
        margin = best_score - second
        if best_score < threshold or (require_margin and margin < CONFIDENCE_MARGIN):
            return PromptPrediction("unknown", best_score, margin, scores)
        return PromptPrediction(names[best_idx], best_score, margin, scores)


class AudioClassifier:
    def __init__(self, embedder: AudioEmbedder, ontology: Ontology):
        self.embedder = embedder
        self.ontology = ontology
        self.prompts = PromptBank(embedder)

    def classify(
        self,
        audio_emb: np.ndarray,
        ontology: Ontology | None = None,
        duration: float = 0.0,
        tag_genre: str = "",
        filename: str = "",
    ) -> Classification:
        ontology = ontology or self.ontology
        result = Classification()

        content = self.prompts.predict(
            audio_emb, ontology.get_content_type_prompts()
        )
        result.content_type_confidence = round(content.score, 4)
        content_type = content.label
        if content_type == "unknown" and duration > MIN_MUSIC_DURATION:
            content_type = "music"

        # Полноценные песни CLAP иногда относит к singing/speech. Для длинных
        # треков это почти всегда music, иначе мы теряем жанр и настроение.
        if content_type in {"singing", "speech"} and duration >= LONG_FORM_THRESHOLD:
            music_score = content.scores.get("music", 0.0)
            if music_score >= content.score - 0.12:
                content_type = "music"
        result.content_type = content_type
        if content_type == "singing":
            result.has_vocal = True

        if content_type not in ("music", "singing"):
            result.confidences = {
                "content_type": result.content_type_confidence,
                "content_type_margin": round(content.margin, 4),
            }
            return result

        genre_pred = self.prompts.predict(
            audio_emb, ontology.get_flat_genre_prompts(), require_margin=False
        )
        result.genre_confidence = round(genre_pred.score, 4)
        result.genre_candidates = sorted(
            ((name, round(score, 4)) for name, score in genre_pred.scores.items()),
            key=lambda item: item[1],
            reverse=True,
        )[:3]

        filename_genre = ""
        if filename:
            filename_genre = (ontology.extract_concepts(filename)["genres"] or [""])[0]
        tag_mapped = ontology.map_genre_value(tag_genre)

        clap_genre = genre_pred.label
        if tag_mapped:
            result.genre = tag_mapped
            result.genre_source = "tag"
        elif filename_genre:
            result.genre = filename_genre
            result.genre_source = "filename"
        elif clap_genre != "unknown":
            result.genre = clap_genre
            result.genre_source = "clap"

        if (
            result.genre
            and clap_genre != "unknown"
            and not ontology.is_genre_related(result.genre, clap_genre)
        ):
            result.confidences["genre_conflict"] = (
                f"{result.genre_source}={result.genre} vs clap={clap_genre}"
            )

        mood_pred = self.prompts.predict(
            audio_emb, ontology.get_mood_prompts(), require_margin=False
        )
        result.mood = "" if mood_pred.label == "unknown" else mood_pred.label
        result.mood_confidence = round(mood_pred.score, 4)
        if result.mood and result.genre:
            consistent = ontology.mood_is_consistent_with_genre(
                result.mood, result.genre
            )
            result.confidences["mood_genre_consistency"] = consistent
            if not consistent:
                related = ontology.get_related_moods(result.genre)
                candidates = [
                    (mood, score)
                    for mood, score in mood_pred.scores.items()
                    if mood in related and score >= CONFIDENCE_THRESHOLD
                ]
                if candidates:
                    result.mood, score = max(candidates, key=lambda item: item[1])
                    result.mood_confidence = round(float(score), 4)
                    result.confidences["mood_adjusted_by_ontology"] = True
                else:
                    result.mood_confidence = round(
                        max(0.0, result.mood_confidence - 0.05), 4
                    )

        result.confidences.update(
            {
                "content_type": result.content_type_confidence,
                "content_type_margin": round(content.margin, 4),
                "genre_clap": result.genre_confidence,
                "genre_margin": round(genre_pred.margin, 4),
                "mood": result.mood_confidence,
                "mood_margin": round(mood_pred.margin, 4),
            }
        )
        return result
