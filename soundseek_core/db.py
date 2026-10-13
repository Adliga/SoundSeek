import faiss
import numpy as np
import pickle
from typing import List, Tuple, Set, Optional

from .models import Track


class VectorDB:
    def __init__(self, audio_dim: int = 512, text_dim: int = 384):
        self.audio_dim = audio_dim
        self.text_dim = text_dim

        self.audio_index = faiss.IndexFlatIP(audio_dim)
        self.text_index = faiss.IndexFlatIP(text_dim)

        self.tracks: List[Track] = []
        self.ids: Set[str] = set()
        self.text_embeddings: List[Optional[np.ndarray]] = []

    def contains(self, track_id: str) -> bool:
        return track_id in self.ids

    def add(
        self,
        audio_embedding: np.ndarray,
        track: Track,
        text_embedding: Optional[np.ndarray] = None,
    ) -> None:
        audio_emb = audio_embedding.astype("float32").reshape(1, -1)
        faiss.normalize_L2(audio_emb)
        self.audio_index.add(audio_emb)

        if text_embedding is not None:
            text_emb = text_embedding.astype("float32").reshape(1, -1)
            faiss.normalize_L2(text_emb)
            self.text_index.add(text_emb)
            self.text_embeddings.append(text_embedding)
        else:
            zero = np.zeros((1, self.text_dim), dtype="float32")
            self.text_index.add(zero)
            self.text_embeddings.append(None)

        self.tracks.append(track)
        self.ids.add(track.id)

    def update_text(self, track_id: str, text_embedding: np.ndarray) -> None:
        """Пересобирает текстовый индекс, добавляя эмбеддинг для указанного трека."""
        if track_id not in self.ids:
            return
        idx = next(i for i, t in enumerate(self.tracks) if t.id == track_id)
        self.text_embeddings[idx] = text_embedding

        new_index = faiss.IndexFlatIP(self.text_dim)
        for emb in self.text_embeddings:
            if emb is None:
                new_index.add(np.zeros((1, self.text_dim), dtype="float32"))
            else:
                e = emb.astype("float32").reshape(1, -1)
                faiss.normalize_L2(e)
                new_index.add(e)
        self.text_index = new_index

    def search_audio(self, query_emb: np.ndarray, top_k: int = 5) -> List[Tuple[Track, float]]:
        return self._search(self.audio_index, query_emb, top_k)

    def search_text(self, query_emb: np.ndarray, top_k: int = 5) -> List[Tuple[Track, float]]:
        return self._search(self.text_index, query_emb, top_k)

    def _search(self, index, query_emb: np.ndarray, top_k: int) -> List[Tuple[Track, float]]:
        emb = query_emb.astype("float32").reshape(1, -1)
        faiss.normalize_L2(emb)
        scores, indices = index.search(emb, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                results.append((self.tracks[idx], float(score)))
        return results

    def save(self, path: str) -> None:
        faiss.write_index(self.audio_index, f"{path}.audio.faiss")
        faiss.write_index(self.text_index, f"{path}.text.faiss")
        with open(f"{path}.tracks", "wb") as f:
            pickle.dump({
                "tracks": self.tracks,
                "ids": self.ids,
                "text_embeddings": self.text_embeddings,
            }, f)

    def load(self, path: str) -> None:
        self.audio_index = faiss.read_index(f"{path}.audio.faiss")
        self.text_index = faiss.read_index(f"{path}.text.faiss")
        with open(f"{path}.tracks", "rb") as f:
            data = pickle.load(f)
        self.tracks = data["tracks"]
        self.ids = data["ids"]
        self.text_embeddings = data.get("text_embeddings", [None] * len(self.tracks))

    def __len__(self) -> int:
        return len(self.tracks)