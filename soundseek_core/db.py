"""Векторная база: FAISS + метаданные треков.

База защищена RLock: индексация, фоновое обогащение и поиск могут работать
одновременно. Сохранение атомарное — сначала временные файлы, затем
``os.replace``. Это важно, потому что UI и воркер пишут в одну базу.
"""

from __future__ import annotations

import json
import os
import pickle
import threading
from pathlib import Path
from typing import Iterable, Optional

import faiss
import numpy as np

from .config import DB_VERSION
from .models import Track


class VectorDB:
    def __init__(self, audio_dim: int = 512, text_dim: int = 384):
        self.audio_dim = audio_dim
        self.text_dim = text_dim
        self.audio_index = faiss.IndexFlatIP(audio_dim)
        self.text_index = faiss.IndexFlatIP(text_dim)
        self.tracks: list[Track] = []
        self.ids: set[str] = set()
        self.text_embeddings: list[Optional[np.ndarray]] = []
        self.audio_embeddings: list[np.ndarray] = []
        self.lock = threading.RLock()

    # ---------- Базовые операции ----------
    def contains(self, track_id: str) -> bool:
        with self.lock:
            return track_id in self.ids

    def get(self, track_id: str) -> Optional[Track]:
        with self.lock:
            return next((track for track in self.tracks if track.id == track_id), None)

    def add(
        self,
        audio_embedding: np.ndarray,
        track: Track,
        text_embedding: Optional[np.ndarray] = None,
    ) -> None:
        with self.lock:
            audio_emb = np.asarray(audio_embedding, dtype="float32").reshape(1, -1)
            faiss.normalize_L2(audio_emb)
            self.audio_index.add(audio_emb)
            self.audio_embeddings.append(audio_emb.flatten().copy())

            if text_embedding is not None:
                text_emb = np.asarray(text_embedding, dtype="float32").reshape(1, -1)
                faiss.normalize_L2(text_emb)
                self.text_index.add(text_emb)
                self.text_embeddings.append(text_emb.flatten().copy())
            else:
                self.text_index.add(np.zeros((1, self.text_dim), dtype="float32"))
                self.text_embeddings.append(None)

            self.tracks.append(track)
            self.ids.add(track.id)

    def replace(
        self,
        track_id: str,
        audio_embedding: np.ndarray,
        track: Track,
        text_embedding: Optional[np.ndarray] = None,
    ) -> bool:
        """Атомарно заменяет трек или добавляет его, если он исчез.

        В отличие от ``remove`` + ``add``, при ошибке до вызова метода старые
        данные остаются в базе. Это важно для инкрементальной индексации:
        сбой одного файла не должен удалять уже проиндексированный трек.
        """
        with self.lock:
            index = next(
                (i for i, item in enumerate(self.tracks) if item.id == track_id),
                None,
            )
            if index is None:
                self.add(audio_embedding, track, text_embedding=text_embedding)
                return False

            audio_emb = np.asarray(audio_embedding, dtype="float32").reshape(-1)
            faiss.normalize_L2(audio_emb.reshape(1, -1))
            self.audio_embeddings[index] = audio_emb.copy()
            if text_embedding is None:
                self.text_embeddings[index] = None
            else:
                text_emb = np.asarray(text_embedding, dtype="float32").reshape(-1)
                faiss.normalize_L2(text_emb.reshape(1, -1))
                self.text_embeddings[index] = text_emb.copy()
            self.tracks[index] = track
            self.ids = {item.id for item in self.tracks}
            self._rebuild_audio_index()
            self._rebuild_text_index()
            return True

    def update_text(self, track_id: str, text_embedding: np.ndarray) -> None:
        """Пересобирает текстовый индекс после изменения текста песни."""
        with self.lock:
            if track_id not in self.ids:
                return
            index = next(
                (i for i, track in enumerate(self.tracks) if track.id == track_id),
                None,
            )
            if index is None:
                return
            self.text_embeddings[index] = np.asarray(
                text_embedding, dtype="float32"
            ).flatten().copy()
            self._rebuild_text_index()

    def remove(self, track_ids: Iterable[str]) -> int:
        """Удаляет треки и пересобирает оба FAISS-индекса."""
        ids = set(track_ids)
        with self.lock:
            if not ids:
                return 0
            self._ensure_audio_embeddings()
            keep = [i for i, track in enumerate(self.tracks) if track.id not in ids]
            removed = len(self.tracks) - len(keep)
            if not removed:
                return 0
            self.tracks = [self.tracks[i] for i in keep]
            self.text_embeddings = [self.text_embeddings[i] for i in keep]
            self.audio_embeddings = [self.audio_embeddings[i] for i in keep]
            self.ids = {track.id for track in self.tracks}
            self._rebuild_audio_index()
            self._rebuild_text_index()
            return removed

    def reassign_ids(self, mapping: dict[str, str]) -> None:
        """Меняет старые stem-id на стабильные id без пересборки FAISS."""
        with self.lock:
            if not mapping:
                return
            for track in self.tracks:
                new_id = mapping.get(track.id)
                if new_id:
                    track.id = new_id
            self.ids = {track.id for track in self.tracks}

    def replace_track(self, track_id: str, track: Track) -> bool:
        """Заменяет метаданные трека, не трогая эмбеддинги."""
        with self.lock:
            for index, old in enumerate(self.tracks):
                if old.id == track_id:
                    self.tracks[index] = track
                    return True
            return False

    def snapshot(self) -> list[Track]:
        with self.lock:
            return list(self.tracks)

    def text_embedding(self, track_id: str) -> Optional[np.ndarray]:
        """Возвращает текстовый эмбеддинг трека, если он уже посчитан."""
        with self.lock:
            index = next(
                (i for i, track in enumerate(self.tracks) if track.id == track_id),
                None,
            )
            if index is None:
                return None
            embedding = self.text_embeddings[index]
            if embedding is None:
                return None
            return np.asarray(embedding, dtype="float32").copy()

    def has_text_embeddings(self) -> bool:
        with self.lock:
            return any(
                embedding is not None and float(np.linalg.norm(embedding)) > 1e-9
                for embedding in self.text_embeddings
            )

    def audio_matrix(self) -> np.ndarray:
        with self.lock:
            self._ensure_audio_embeddings()
            if not self.audio_embeddings:
                return np.zeros((0, self.audio_dim), dtype="float32")
            return np.vstack(self.audio_embeddings).astype("float32")

    # ---------- Поиск ----------
    def search_audio(self, query_emb: np.ndarray, top_k: int = 5) -> list[tuple[Track, float]]:
        with self.lock:
            return self._search(self.audio_index, query_emb, top_k)

    def search_text(self, query_emb: np.ndarray, top_k: int = 5) -> list[tuple[Track, float]]:
        with self.lock:
            results = self._search(self.text_index, query_emb, top_k)
            # Нулевые векторы — это треки без текста. Они не должны попадать
            # в результаты лирического поиска.
            filtered = []
            for track, score in results:
                index = next(
                    (i for i, item in enumerate(self.tracks) if item.id == track.id),
                    None,
                )
                if index is None:
                    continue
                emb = self.text_embeddings[index]
                if emb is None:
                    continue
                if float(np.linalg.norm(emb)) < 1e-9:
                    continue
                if score <= 0:
                    continue
                filtered.append((track, score))
            return filtered

    def _search(self, index, query_emb: np.ndarray, top_k: int) -> list[tuple[Track, float]]:
        if not self.tracks or top_k <= 0:
            return []
        emb = np.asarray(query_emb, dtype="float32").reshape(1, -1)
        faiss.normalize_L2(emb)
        scores, indices = index.search(emb, min(top_k, len(self.tracks)))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(self.tracks):
                results.append((self.tracks[int(idx)], float(score)))
        return results

    # ---------- Пересборка индексов ----------
    def _rebuild_audio_index(self) -> None:
        self.audio_index = faiss.IndexFlatIP(self.audio_dim)
        for embedding in self.audio_embeddings:
            vector = np.asarray(embedding, dtype="float32").reshape(1, -1)
            faiss.normalize_L2(vector)
            self.audio_index.add(vector)

    def _rebuild_text_index(self) -> None:
        self.text_index = faiss.IndexFlatIP(self.text_dim)
        for embedding in self.text_embeddings:
            if embedding is None:
                self.text_index.add(np.zeros((1, self.text_dim), dtype="float32"))
                continue
            vector = np.asarray(embedding, dtype="float32").reshape(1, -1)
            faiss.normalize_L2(vector)
            self.text_index.add(vector)

    def _ensure_audio_embeddings(self) -> None:
        if len(self.audio_embeddings) == len(self.tracks):
            return
        if len(self.tracks) == 0:
            self.audio_embeddings = []
            return
        try:
            matrix = self.audio_index.reconstruct_n(0, len(self.tracks))
            self.audio_embeddings = [
                np.asarray(row, dtype="float32") for row in matrix
            ]
        except Exception:
            self.audio_embeddings = []

    # ---------- Сохранение / загрузка ----------
    def save(self, path: str | Path) -> None:
        base = Path(path)
        base.parent.mkdir(parents=True, exist_ok=True)
        with self.lock:
            self._ensure_audio_embeddings()
            audio_path = Path(f"{base}.audio.faiss")
            text_path = Path(f"{base}.text.faiss")
            tracks_path = Path(f"{base}.tracks")
            manifest_path = Path(f"{base}.manifest.json")

            audio_tmp = audio_path.with_suffix(audio_path.suffix + ".tmp")
            text_tmp = text_path.with_suffix(text_path.suffix + ".tmp")
            tracks_tmp = tracks_path.with_suffix(tracks_path.suffix + ".tmp")
            manifest_tmp = manifest_path.with_suffix(manifest_path.suffix + ".tmp")

            faiss.write_index(self.audio_index, str(audio_tmp))
            faiss.write_index(self.text_index, str(text_tmp))
            with open(tracks_tmp, "wb") as handle:
                pickle.dump(
                    {
                        "version": DB_VERSION,
                        "tracks": self.tracks,
                        "ids": self.ids,
                        "text_embeddings": self.text_embeddings,
                        "audio_embeddings": self.audio_embeddings,
                    },
                    handle,
                    protocol=pickle.HIGHEST_PROTOCOL,
                )
            manifest = {
                "version": DB_VERSION,
                "tracks": len(self.tracks),
                "audio_dim": self.audio_dim,
                "text_dim": self.text_dim,
            }
            manifest_tmp.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            os.replace(audio_tmp, audio_path)
            os.replace(text_tmp, text_path)
            os.replace(tracks_tmp, tracks_path)
            os.replace(manifest_tmp, manifest_path)

    def load(self, path: str | Path) -> None:
        base = Path(path)
        with self.lock:
            self.audio_index = faiss.read_index(str(f"{base}.audio.faiss"))
            self.text_index = faiss.read_index(str(f"{base}.text.faiss"))
            self.audio_dim = int(self.audio_index.d)
            self.text_dim = int(self.text_index.d)
            with open(f"{base}.tracks", "rb") as handle:
                data = pickle.load(handle)

            self.tracks = data["tracks"]
            self.ids = set(data.get("ids") or {track.id for track in self.tracks})
            self.text_embeddings = data.get("text_embeddings") or []
            self.audio_embeddings = data.get("audio_embeddings") or []

            if len(self.text_embeddings) < len(self.tracks):
                self.text_embeddings.extend(
                    [None] * (len(self.tracks) - len(self.text_embeddings))
                )
            self.text_embeddings = self.text_embeddings[: len(self.tracks)]
            self._ensure_audio_embeddings()

            if self.audio_index.ntotal != len(self.tracks):
                raise ValueError(
                    "Повреждён индекс: audio.faiss содержит "
                    f"{self.audio_index.ntotal} векторов, а tracks — "
                    f"{len(self.tracks)} записей"
                )
            if self.text_index.ntotal != len(self.tracks):
                self._rebuild_text_index()
            self.ids = {track.id for track in self.tracks}

    def __len__(self) -> int:
        with self.lock:
            return len(self.tracks)
