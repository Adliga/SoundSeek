"""Тяжёлое обогащение трека: Demucs + Whisper + текстовый эмбеддинг."""

from __future__ import annotations

import re
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


def _language_hint(track: Track) -> Optional[str]:
    """Подсказывает Whisper язык по письменности названия и исполнителя.

    Автоопределение на отделённом вокале иногда ошибается: русский трек
    может быть принят за латынь, после чего Whisper выдаёт набор тире или
    транслитерацию. Для кириллицы и японской письменности подсказка
    надёжнее, чем автоопределение по короткому вокальному фрагменту.
    """
    text = " ".join(
        [
            track.tags.title,
            track.tags.artist,
            track.tags.album,
            Path(track.path).stem,
        ]
    )
    if re.search(r"[іїєґІЇЄҐ]", text):
        return "uk"
    if re.search(r"[А-Яа-яЁё]", text):
        return "ru"
    if re.search(r"[ぁ-んァ-ヶ]", text):
        return "ja"
    if re.search(r"[가-힣]", text):
        return "ko"
    return None


def _max_token_run(tokens: list[str]) -> int:
    best = 0
    current = 0
    previous = ""
    for token in tokens:
        if token == previous:
            current += 1
        else:
            previous = token
            current = 1
        best = max(best, current)
    return best


def _looks_like_hallucination(text: str) -> bool:
    """Отсеивает характерные зацикливания Whisper на музыке и шуме."""
    text = (text or "").strip()
    if not text:
        return False
    if re.search(r"(.)\1{10,}", text, flags=re.UNICODE):
        return True
    tokens = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
    if not tokens:
        return False
    if _max_token_run(tokens) > 5:
        return True
    if len(tokens) >= 6 and len(set(tokens)) / len(tokens) < 0.22:
        return True
    return False


class EnrichmentService:
    def __init__(
        self,
        db: VectorDB,
        text_embedder: Callable[[], TextEmbedder],
        save_callback: Callable[[], None],
        whisper_model_size: str | None = None,
    ):
        self.db = db
        self._get_text_embedder = text_embedder
        self._save = save_callback
        # None приходит из AudioIndexer, когда размер не задан явно.
        # Нельзя передавать его в whisper.load_model: там ожидается имя модели.
        self.whisper_model_size = whisper_model_size or WHISPER_MODEL_SIZE
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
        self, audio_path: str, language: Optional[str] = None
    ) -> tuple[str, str, list[LyricsSegment], str]:
        try:
            model = self._get_whisper()
            result = model.transcribe(
                audio_path,
                language=language,
                fp16=False,
                condition_on_previous_text=False,
                no_speech_threshold=0.6,
                logprob_threshold=-1.0,
                temperature=0.0,
            )
            detected_language = str(result.get("language", ""))
            raw_segments = [
                segment
                for segment in result.get("segments", [])
                if str(segment.get("text", "")).strip()
            ]
            kept_segments = []
            for segment in raw_segments:
                text = str(segment.get("text", "")).strip()
                try:
                    compression = float(segment.get("compression_ratio", 0.0))
                except (TypeError, ValueError):
                    compression = 0.0
                # Высокий compression ratio — почти всегда зацикленный
                # «мастер, мастер...» или «Аааа...» на инструментальном
                # фрагменте, а не реальная строка песни.
                if compression > 3.0 or _looks_like_hallucination(text):
                    continue
                kept_segments.append(
                    LyricsSegment(
                        start=float(segment.get("start", 0.0)),
                        end=float(segment.get("end", 0.0)),
                        text=text,
                    )
                )
            text = " ".join(segment.text for segment in kept_segments).strip()
            return text, detected_language, kept_segments, ""
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
                lyrics, language, segments, error = self._transcribe(
                    vocals_path,
                    language=_language_hint(track),
                )
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
