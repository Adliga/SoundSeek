"""Тяжёлое обогащение трека: Demucs + Whisper + текстовый эмбеддинг."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .config import (
    MIN_ENRICH_DURATION,
    MIN_LYRICS_LENGTH,
    WHISPER_MODEL_SIZE,
)
from .db import VectorDB
from .embeddings import TextEmbedder
from .models import LyricsSegment, Track


class EnrichmentService:
    def __init__(
        self,
        db: VectorDB,
        text_embedder: Callable[[], TextEmbedder],
        save_callback: Callable[[], None],
        whisper_model_size: str = WHISPER_MODEL_SIZE,
    ):
        self.db = db
        self._get_text_embedder = text_embedder
        self._save = save_callback
        self.whisper_model_size = whisper_model_size
        self._whisper = None

    def _get_whisper(self):
        if self._whisper is None:
            import whisper

            print(f"Загрузка Whisper ({self.whisper_model_size})...")
            self._whisper = whisper.load_model(self.whisper_model_size)
        return self._whisper

    @staticmethod
    def _separate_vocals(path: str, tmp_dir: str) -> Optional[str]:
        try:
            from demucs_onnx import separate_stem

            separate_stem(path, stem="vocals", output_dir=tmp_dir)
            candidate = Path(tmp_dir) / "vocals.wav"
            if candidate.exists():
                return str(candidate)
            found = list(Path(tmp_dir).rglob("vocals.wav"))
            return str(found[0]) if found else None
        except Exception as exc:
            print(f"    Demucs ошибка: {exc}")
            return None

    def _transcribe(
        self, audio_path: str
    ) -> tuple[str, str, list[LyricsSegment], str]:
        try:
            model = self._get_whisper()
            result = model.transcribe(
                audio_path,
                language=None,
                fp16=False,
                condition_on_previous_text=False,
                no_speech_threshold=0.6,
                logprob_threshold=-1.0,
                temperature=0.0,
            )
            text = str(result.get("text", "")).strip()
            language = str(result.get("language", ""))
            segments = [
                LyricsSegment(
                    start=float(segment.get("start", 0.0)),
                    end=float(segment.get("end", 0.0)),
                    text=str(segment.get("text", "")).strip(),
                )
                for segment in result.get("segments", [])
                if str(segment.get("text", "")).strip()
            ]
            return text, language, segments, ""
        except Exception as exc:
            print(f"    Whisper error: {exc}")
            return "", "", [], str(exc)

    def should_enrich(self, track: Track) -> bool:
        if track.derived.duration and track.derived.duration < MIN_ENRICH_DURATION:
            return False
        return track.derived.content_type in ("music", "singing", "")

    def enrich_single_track(self, track: Track, force: bool = False) -> bool:
        t0 = time.time()
        track.derived.enrich_attempted_at = time.time()
        track.derived.enrich_status = "running"
        track.derived.enrich_error = ""

        if not self.should_enrich(track) and not force:
            track.derived.enrich_status = "skipped"
            track.derived.enrich_error = "слишком короткий трек или не музыка"
            self._save()
            return False

        previous_lyrics = track.derived.lyrics.strip()
        previous_has_vocal = track.derived.has_vocal

        # 1. Встроенный текст из тегов или sidecar-файла имеет приоритет:
        # он точнее Whisper и не требует Demucs. При force пользователь
        # явно просит перераспознать текст, поэтому старый текст не
        # останавливает обработку.
        if not force and previous_lyrics:
            track.derived.has_vocal = True
            track.derived.enrich_status = "done"
            self._update_text_embedding(track)
            self._save()
            print(f"  [встроенный текст] {track.id}")
            return True

        lyrics = ""
        language = ""
        segments: list[LyricsSegment] = []
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                vocals_path = self._separate_vocals(track.path, tmp_dir)
                if not vocals_path:
                    raise RuntimeError(
                        "Demucs did not create a vocal track"
                    )
                lyrics, language, segments, error = self._transcribe(vocals_path)
                if error:
                    raise RuntimeError(f"Whisper: {error}")
        except Exception as exc:
            track.derived.enrich_status = "error"
            track.derived.enrich_error = str(exc)
            self._save()
            print(f"  enrich error for {track.id}: {exc}")
            return False

        if len(lyrics) >= MIN_LYRICS_LENGTH:
            track.derived.lyrics = lyrics
            track.derived.lyrics_language = language
            track.derived.lyrics_segments = segments
            track.derived.lyrics_source = "whisper"
            track.derived.has_vocal = True
            track.derived.enrich_status = "done"
            self._update_text_embedding(track)
        elif previous_lyrics:
            # Повторное распознавание не должно уничтожать уже сохранённый
            # текст: Whisper мог ошибиться на тихой дорожке. Пользователь
            # может очистить текст вручную, если он действительно неверен.
            track.derived.lyrics = previous_lyrics
            track.derived.has_vocal = (
                previous_has_vocal if previous_has_vocal is not None else True
            )
            track.derived.enrich_status = "done"
            self._update_text_embedding(track)
            print(
                "  Распознавание не дало нового текста; сохранён прежний."
            )
        else:
            track.derived.lyrics = ""
            track.derived.lyrics_segments = []
            track.derived.has_vocal = False
            track.derived.enrich_status = "done"
            self.db.update_text(
                track.id, np.zeros(self.db.text_dim, dtype="float32")
            )

        self._save()
        elapsed = time.time() - t0
        print(
            f"  [{elapsed:.1f} с] "
            f"{'вокал' if track.derived.has_vocal else 'без вокала'} | {track.id}"
        )
        return bool(track.derived.has_vocal)

    def _update_text_embedding(self, track: Track) -> None:
        text = track.derived.lyrics.strip()
        if not text:
            self.db.update_text(track.id, np.zeros(self.db.text_dim, dtype="float32"))
            return
        embedder = self._get_text_embedder()
        self.db.update_text(track.id, embedder.encode(text, is_query=False))

    def enrich_many(
        self,
        max_tracks: int | None = None,
        force: bool = False,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> int:
        targets = [
            track
            for track in self.db.snapshot()
            if force
            or (
                track.derived.enrich_status in ("", "idle")
                and track.derived.content_type in ("music", "singing", "")
                and track.derived.duration >= MIN_ENRICH_DURATION
            )
        ]
        if max_tracks:
            targets = targets[:max_tracks]
        total = len(targets)
        print(f"Треков для обогащения: {total}")
        for index, track in enumerate(targets, 1):
            self.enrich_single_track(track, force=force)
            if on_progress:
                try:
                    on_progress(index, total, track.id)
                except Exception:
                    pass
        return total
