"""Обёртки над нейросетевыми эмбеддерами.

Здесь сосредоточена вся работа с CLAP и текстовой sentence-transformer
моделью. Классификатор и поиск не знают деталей загрузки моделей.
"""

from __future__ import annotations

import os
from typing import Iterable

import numpy as np
import torch
import torch.nn.functional as F
from huggingface_hub import snapshot_download
from sentence_transformers import SentenceTransformer
from transformers import ClapModel, ClapProcessor

from .audio import split_into_windows
from .config import (
    AUDIO_EMBEDDING_DIM,
    CLAP_MODEL_NAME,
    CLAP_WINDOW_SECONDS,
    INDEX_SEGMENTS,
    SAMPLE_RATE,
    TEXT_MODEL_FALLBACK,
    TEXT_MODEL_NAME,
)


class AudioEmbedder:
    """CLAP-эмбеддинги с детерминированной нарезкой на 10-секундные окна."""

    def __init__(self, model_name: str = CLAP_MODEL_NAME):
        self.model_name = model_name
        print(f"Загрузка CLAP ({model_name})...")
        self.model = ClapModel.from_pretrained(model_name)
        self.processor = ClapProcessor.from_pretrained(model_name)
        self.model.eval()

    @torch.inference_mode()
    def _embed_window(self, audio: np.ndarray) -> np.ndarray:
        inputs = self.processor(
            audio=audio,
            sampling_rate=SAMPLE_RATE,
            return_tensors="pt",
            truncation=False,
            padding="repeatpad",
        )
        outputs = self.model.get_audio_features(**inputs)
        emb = outputs.pooler_output if hasattr(outputs, "pooler_output") else outputs
        emb = F.normalize(emb.float(), dim=-1)
        return emb.numpy().flatten()

    def embed_audio(self, audio: np.ndarray, segments: int = INDEX_SEGMENTS) -> np.ndarray:
        windows = split_into_windows(
            np.asarray(audio, dtype="float32"),
            window_seconds=CLAP_WINDOW_SECONDS,
            segments=segments,
        )
        vectors = [self._embed_window(window) for window in windows]
        mean = np.mean(vectors, axis=0)
        norm = float(np.linalg.norm(mean))
        if norm > 1e-9:
            mean = mean / norm
        return mean.astype("float32")

    @torch.inference_mode()
    def embed_text(self, text: str) -> np.ndarray:
        inputs = self.processor(
            text=[text],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=77,
        )
        outputs = self.model.get_text_features(**inputs)
        emb = outputs.pooler_output if hasattr(outputs, "pooler_output") else outputs
        emb = F.normalize(emb.float(), dim=-1)
        return emb.numpy().flatten().astype("float32")

    @torch.inference_mode()
    def embed_prompts(self, prompts: dict[str, str]) -> tuple[list[str], torch.Tensor]:
        if not prompts:
            return [], torch.empty((0, AUDIO_EMBEDDING_DIM))
        names = list(prompts)
        inputs = self.processor(
            text=[prompts[name] for name in names],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=77,
        )
        outputs = self.model.get_text_features(**inputs)
        embeddings = outputs.pooler_output if hasattr(outputs, "pooler_output") else outputs
        return names, F.normalize(embeddings.float(), dim=-1)


def _model_is_cached(model_name: str) -> bool:
    try:
        snapshot_download(model_name, local_files_only=True)
        return True
    except Exception:
        return False


class TextEmbedder:
    """Мультиязычные эмбеддинги для поиска по строкам песен.

    Основная модель — multilingual-e5-small. Если её не удалось загрузить
    (нет сети / нет весов), используется английская MiniLM, чтобы приложение
    оставалось работоспособным.
    """

    def __init__(
        self,
        model_name: str = TEXT_MODEL_NAME,
        fallback: str = TEXT_MODEL_FALLBACK,
    ):
        self.requested_model_name = model_name
        self.model_name = model_name
        allow_download = os.getenv("SOUNDSEEK_ALLOW_MODEL_DOWNLOAD", "0") == "1"
        if not _model_is_cached(model_name):
            if allow_download:
                print(f"Загрузка текстовой модели ({model_name})...")
            else:
                print(
                    f"Текстовая модель {model_name} не найдена в кэше; "
                    f"используется {fallback}. "
                    "Для загрузки мультиязычной модели задайте "
                    "SOUNDSEEK_ALLOW_MODEL_DOWNLOAD=1."
                )
                self.model_name = fallback
        else:
            print(f"Загрузка текстовой модели ({model_name})...")
        try:
            self.model = SentenceTransformer(self.model_name, device="cpu")
        except Exception as exc:  # pragma: no cover - зависит от окружения
            print(f"  не удалось загрузить {self.model_name}: {exc}")
            print(f"  откат на {fallback}")
            self.model_name = fallback
            self.model = SentenceTransformer(fallback, device="cpu")
        self.is_e5 = "e5" in self.model_name.lower()

    def _with_prefix(self, text: str, is_query: bool) -> str:
        if not self.is_e5:
            return text
        return ("query: " if is_query else "passage: ") + text

    def encode(self, text: str, is_query: bool = False) -> np.ndarray:
        return self.model.encode(
            self._with_prefix(text, is_query),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")

    def encode_batch(
        self,
        texts: Iterable[str],
        is_query: bool = False,
    ) -> np.ndarray:
        prepared = [self._with_prefix(text, is_query) for text in texts]
        return self.model.encode(
            prepared,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")
