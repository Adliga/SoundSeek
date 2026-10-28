"""Оркестрация индексации аудиотеки.

Модуль отвечает за жизненный цикл трека: найти файл, проверить изменения,
посчитать эмбеддинги, классифицировать, сохранить в FAISS и обновить
метаданные. Тяжёлая логика вынесена в ``audio``, ``embeddings``,
``classifier``, ``enrichment`` и ``db``.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np

from .audio import index_window_count, load_track_audio, middle_segment
from .classifier import AudioClassifier, Classification
from .config import (
    AUDIO_EMBEDDING_VERSION,
    AUDIO_EXTENSIONS,
    COVERS_DIR,
    EXCLUDED_DIRS,
    EXCLUDED_PREFIXES,
    INDEX_WINDOW_SECONDS,
    SAMPLE_RATE,
    TRACKS_DIR,
)
from .db import VectorDB
from .embeddings import AudioEmbedder, TextEmbedder
from .enrichment import EnrichmentService
from .melody import extract_chroma, extract_melody
from .models import DerivedData, FileTags, Track
from .ontology import Ontology
from .tags import read_sidecar_lyrics, read_tags, save_cover


@dataclass
class IndexStats:
    total_files: int = 0
    added: int = 0
    updated: int = 0
    skipped: int = 0
    removed: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"файлов: {self.total_files}, добавлено: {self.added}, "
            f"обновлено: {self.updated}, пропущено: {self.skipped}, "
            f"удалено: {self.removed}, ошибок: {self.failed}"
        )


def stable_track_id(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/").strip("/")
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]


class AudioIndexer:
    def __init__(
        self,
        db_path: str | Path | None = None,
        ontology: Ontology | None = None,
        load_models: bool = True,
        whisper_model_size: str | None = None,
    ):
        self.ontology = ontology or Ontology()
        self.db = VectorDB(audio_dim=512, text_dim=384)
        self.db_path = str(db_path) if db_path else None
        self._audio_embedder: AudioEmbedder | None = None
        self._text_embedder: TextEmbedder | None = None
        self._classifier: AudioClassifier | None = None
        self._load_models = load_models

        if self.db_path and Path(f"{self.db_path}.audio.faiss").exists():
            self.db.load(self.db_path)
            print(f"Загружено {len(self.db)} треков из {self.db_path}")

        self.enrichment = EnrichmentService(
            db=self.db,
            text_embedder=lambda: self.text_embedder,
            save_callback=self.save,
            whisper_model_size=whisper_model_size,
        )
        if load_models:
            _ = self.audio_embedder
            _ = self.classifier

    # ---------- Ленивая загрузка моделей ----------
    @property
    def audio_embedder(self) -> AudioEmbedder:
        if self._audio_embedder is None:
            self._audio_embedder = AudioEmbedder()
        return self._audio_embedder

    @property
    def text_embedder(self) -> TextEmbedder:
        if self._text_embedder is None:
            self._text_embedder = TextEmbedder()
        return self._text_embedder

    @property
    def classifier(self) -> AudioClassifier:
        if self._classifier is None:
            self._classifier = AudioClassifier(self.audio_embedder, self.ontology)
        return self._classifier

    # ---------- Эмбеддинги для совместимости ----------
    def get_audio_embedding(self, audio: np.ndarray, segments: int = 1) -> np.ndarray:
        return self.audio_embedder.embed_audio(audio, segments=segments)

    def get_text_embedding(self, text: str) -> np.ndarray:
        return self.text_embedder.encode(text, is_query=False)

    def get_query_text_embedding(self, text: str) -> np.ndarray:
        return self.audio_embedder.embed_text(text)

    def classify_audio(
        self,
        audio_emb: np.ndarray,
        ontology: Ontology | None = None,
        duration: float = 0.0,
        tag_genre: str = "",
        filename: str = "",
    ) -> Classification:
        return self.classifier.classify(
            audio_emb,
            ontology=ontology or self.ontology,
            duration=duration,
            tag_genre=tag_genre,
            filename=filename,
        )

    # ---------- Пути и идентификаторы ----------
    @staticmethod
    def _relative_to_root(path: Path, root: Path) -> str:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return path.name

    def _library_root(self, folder: str | Path | None = None) -> Path:
        return Path(folder).resolve() if folder else TRACKS_DIR.resolve()

    def _track_path(self, track: Track) -> Path:
        path = Path(track.path)
        if path.exists():
            return path
        if track.relative_path:
            candidate = TRACKS_DIR / track.relative_path
            if candidate.exists():
                return candidate
        return path

    def _build_track(
        self,
        path: Path,
        relative_path: str,
        raw_tags: dict[str, Any],
        cover_path: str,
        duration: float,
        audio_emb: np.ndarray,
        old_track: Track | None = None,
    ) -> Track:
        tags = FileTags(
            title=raw_tags.get("title", ""),
            artist=raw_tags.get("artist", ""),
            album=raw_tags.get("album", ""),
            album_artist=raw_tags.get("album_artist", ""),
            year=raw_tags.get("year"),
            track_number=raw_tags.get("track_number"),
            disc_number=raw_tags.get("disc_number"),
            genre=raw_tags.get("genre", ""),
            composer=raw_tags.get("composer", ""),
            comment=raw_tags.get("comment", ""),
            cover_path=cover_path,
        )

        classification = self.classifier.classify(
            audio_emb,
            self.ontology,
            duration=duration,
            tag_genre=tags.genre,
            filename=path.name,
        )

        lyrics = str(raw_tags.get("_lyrics", "") or "").strip()
        lyrics_source = str(raw_tags.get("_lyrics_source", "") or "")
        if not lyrics:
            lyrics, lyrics_source = read_sidecar_lyrics(path)
        if lyrics and duration >= 30:
            # Встроенный текст — сильный признак того, что это песня.
            if classification.content_type in ("", "unknown", "speech"):
                classification.content_type = "music"
            classification.has_vocal = True

        derived = DerivedData(
            content_type=classification.content_type,
            content_type_confidence=classification.content_type_confidence,
            genre=classification.genre,
            genre_source=classification.genre_source,
            genre_confidence=classification.genre_confidence,
            mood=classification.mood,
            mood_confidence=classification.mood_confidence,
            has_vocal=classification.has_vocal,
            lyrics=lyrics,
            lyrics_source=lyrics_source,
            duration=duration,
            confidences=classification.confidences,
            enrich_status="done" if lyrics else "idle",
        )

        track = Track(
            id=stable_track_id(relative_path),
            path=str(path.resolve()),
            tags=tags,
            derived=derived,
            relative_path=relative_path,
            file_size=path.stat().st_size,
            file_mtime=path.stat().st_mtime,
            index_version=AUDIO_EMBEDDING_VERSION,
        )

        # При переиндексации сохраняем ручные правки, чтобы sync не стирал
        # заметки и вручную исправленный текст.
        if old_track is not None:
            track.manual_fields = list(old_track.manual_fields)
            if "title" in track.manual_fields:
                track.tags.title = old_track.tags.title
            if "artist" in track.manual_fields:
                track.tags.artist = old_track.tags.artist
            if "album" in track.manual_fields:
                track.tags.album = old_track.tags.album
            if "year" in track.manual_fields:
                track.tags.year = old_track.tags.year
            if "tag_genre" in track.manual_fields:
                track.tags.genre = old_track.tags.genre
                mapped = self.ontology.map_genre_value(old_track.tags.genre)
                if mapped and "derived_genre" not in track.manual_fields:
                    track.derived.genre = mapped
                    track.derived.genre_source = "tag"
            if "derived_genre" in track.manual_fields:
                track.derived.genre = old_track.derived.genre
                track.derived.genre_source = old_track.derived.genre_source
                if old_track.derived.genre:
                    track.derived.content_type = "music"
            if "derived_mood" in track.manual_fields:
                track.derived.mood = old_track.derived.mood
            track.derived.user_notes = old_track.derived.user_notes
            if old_track.derived.lyrics:
                track.derived.lyrics = old_track.derived.lyrics
                track.derived.lyrics_source = (
                    old_track.derived.lyrics_source or "legacy"
                )
                track.derived.lyrics_segments = old_track.derived.lyrics_segments
                track.derived.lyrics_language = old_track.derived.lyrics_language
                track.derived.has_vocal = True
                track.derived.enrich_status = "done"
            elif old_track.derived.enrich_status in ("done", "skipped", "error"):
                track.derived.enrich_status = old_track.derived.enrich_status
                track.derived.has_vocal = old_track.derived.has_vocal
                track.derived.enrich_error = old_track.derived.enrich_error
        if "derived_mood" not in track.manual_fields:
            self._apply_title_mood_hint(track)
        return track

    def _apply_title_mood_hint(self, track: Track) -> None:
        """Уточняет настроение по явному слову в названии.

        Zero-shot CLAP иногда выбирает настроение с минимальной маржой.
        Если в названии или имени файла есть ровно одно настроение
        онтологии (``Lonely Day``), оно служит более надёжным сигналом.
        Ручная правка настроения всегда имеет приоритет.
        """
        if track.derived.content_type not in ("", "music", "singing"):
            return
        text = f"{track.tags.title} {Path(track.path).stem}"
        moods = self.ontology.extract_concepts(text)["moods"]
        if len(set(moods)) != 1:
            return
        hint = moods[0]
        current = track.derived.mood
        if current and self.ontology.is_mood_related(current, hint):
            return
        track.derived.mood = hint
        track.derived.mood_confidence = max(
            track.derived.mood_confidence, 0.20
        )
        track.derived.confidences["mood_title_hint"] = hint

    # ---------- Индексация ----------
    def index_file_light(
        self,
        path: str | Path,
        force: bool = False,
        library_root: str | Path | None = None,
        old_track: Track | None = None,
    ) -> Optional[Track]:
        path = Path(path)
        root = self._library_root(library_root)
        relative_path = self._relative_to_root(path, root)
        track_id = stable_track_id(relative_path)

        existing = self.db.get(track_id)
        if existing and not force:
            if (
                existing.file_mtime == path.stat().st_mtime
                and existing.file_size == path.stat().st_size
                and existing.index_version == AUDIO_EMBEDDING_VERSION
            ):
                return None
            old_track = old_track or existing

        if old_track is None and existing is not None:
            old_track = existing

        t0 = time.time()
        # CLAP обучался на 10-секундных фрагментах, поэтому весь трек
        # представляется набором окон по всей длительности, а не только
        # средними 30 секундами. Это важно и для поиска по напеванию:
        # характерный мотив может находиться в начале или в конце трека.
        audio = load_track_audio(path)
        duration = float(audio.size) / float(SAMPLE_RATE)
        audio_emb = self.get_audio_embedding(
            audio,
            segments=index_window_count(duration),
        )

        raw_tags = read_tags(path)
        cover_path = save_cover(raw_tags, track_id, COVERS_DIR)
        if not cover_path and old_track is not None:
            cover_path = old_track.tags.cover_path

        track = self._build_track(
            path=path,
            relative_path=relative_path,
            raw_tags=raw_tags,
            cover_path=cover_path,
            duration=duration,
            audio_emb=audio_emb,
            old_track=old_track,
        )
        if duration >= 10 and track.derived.content_type in (
            "",
            "music",
            "singing",
        ):
            melody_audio = middle_segment(audio, seconds=INDEX_WINDOW_SECONDS)
            track.derived.melody_contour = extract_melody(melody_audio).tolist()
            track.derived.melody_chroma = extract_chroma(melody_audio).tolist()

        text_embedding = None
        if track.derived.lyrics:
            try:
                text_embedding = self.text_embedder.encode(
                    track.derived.lyrics, is_query=False
                )
            except Exception as exc:
                # Не теряем старый текстовый индекс, если модель временно
                # недоступна, а текст песни не менялся.
                text_embedding = self.db.text_embedding(track_id)
                print(
                    f"  Текстовый эмбеддинг не посчитан: {exc}"
                    + ("; оставлен прежний" if text_embedding is not None else "")
                )

        self.db.replace(
            track_id,
            audio_emb,
            track,
            text_embedding=text_embedding,
        )
        if self.db_path:
            self.db.save(self.db_path)

        elapsed = time.time() - t0
        print(
            f"  [{elapsed:.1f} с] {track.derived.content_type}/"
            f"{track.derived.genre or '—'}/{track.derived.mood or '—'} "
            f"[{track.derived.genre_source or '—'}] | {path.name}"
        )
        return track

    def _collect_audio_files(self, root: Path) -> list[Path]:
        files: list[Path] = []
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            relative_parts = path.relative_to(root).parts
            if any(part in EXCLUDED_DIRS for part in relative_parts):
                continue
            if path.name.lower().startswith(EXCLUDED_PREFIXES):
                continue
            files.append(path)
        return sorted(files)

    def _migrate_ids(self, root: Path) -> None:
        """Переводит старые stem-id на стабильные id по относительному пути."""
        mapping: dict[str, str] = {}
        for track in self.db.snapshot():
            if track.relative_path:
                relative = track.relative_path
            else:
                relative = self._relative_to_root(Path(track.path), root)
            new_id = stable_track_id(relative)
            track.relative_path = relative
            if track.id != new_id and new_id not in mapping.values():
                mapping[track.id] = new_id
        if mapping:
            self.db.reassign_ids(mapping)

    def sync_folder(
        self,
        folder: str | Path | None = None,
        force: bool = False,
        progress=None,
    ) -> IndexStats:
        root = self._library_root(folder)
        root.mkdir(parents=True, exist_ok=True)
        self._migrate_ids(root)
        files = self._collect_audio_files(root)
        stats = IndexStats(total_files=len(files))

        files_by_id: dict[str, Path] = {}
        for path in files:
            relative = self._relative_to_root(path, root)
            files_by_id[stable_track_id(relative)] = path

        # Удаляем треки, которых больше нет на диске.
        existing_ids = {track.id for track in self.db.snapshot()}
        missing = existing_ids - set(files_by_id)
        if missing:
            stats.removed = self.db.remove(missing)

        for position, path in enumerate(files, 1):
            relative = self._relative_to_root(path, root)
            track_id = stable_track_id(relative)
            existing = self.db.get(track_id)
            try:
                if force:
                    self.index_file_light(
                        path, force=True, library_root=root, old_track=existing
                    )
                    stats.updated += 1
                elif existing is None:
                    self.index_file_light(path, library_root=root)
                    stats.added += 1
                elif (
                    existing.file_mtime != path.stat().st_mtime
                    or existing.file_size != path.stat().st_size
                    or existing.index_version != AUDIO_EMBEDDING_VERSION
                ):
                    self.index_file_light(
                        path, library_root=root, old_track=existing
                    )
                    stats.updated += 1
                else:
                    stats.skipped += 1
            except Exception as exc:
                stats.failed += 1
                stats.errors.append(f"{path.name}: {exc}")
                print(f"  Ошибка при обработке {path.name}: {exc}")
            if progress is not None:
                try:
                    progress((position, len(files)), desc=path.name)
                except Exception:
                    pass

        if self.db_path:
            self.db.save(self.db_path)
        print(f"Синхронизация: {stats.summary()}")
        return stats

    # Совместимость со старым API.
    def index_folder_light(self, folder: str | Path | None = None, force: bool = False) -> int:
        stats = self.sync_folder(folder, force=force)
        return stats.total_files

    def reset_db(self) -> None:
        self.db = VectorDB(audio_dim=512, text_dim=384)
        self.enrichment.db = self.db
        print("База сброшена.")

    def save(self) -> None:
        if self.db_path:
            self.db.save(self.db_path)

    def remove_track(self, track_id: str) -> bool:
        removed = self.db.remove([track_id])
        if removed:
            self.save()
        return bool(removed)

    # ---------- Обогащение ----------
    def enrich_single_track(self, track: Track, force: bool = False) -> bool:
        return self.enrichment.enrich_single_track(track, force=force)

    def enrich_with_lyrics(
        self,
        max_tracks: int | None = None,
        force: bool = False,
        on_progress=None,
    ) -> int:
        return self.enrichment.enrich_many(
            max_tracks=max_tracks, force=force, on_progress=on_progress
        )

    # ---------- Ручное редактирование ----------
    def update_track_fields(
        self,
        track_id: str,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        year: Optional[int] = None,
        tag_genre: Optional[str] = None,
        derived_genre: Optional[str] = None,
        derived_mood: Optional[str] = None,
        lyrics: Optional[str] = None,
        user_notes: Optional[str] = None,
    ) -> Optional[Track]:
        track = self.db.get(track_id)
        if not track:
            return None

        def mark_manual(field_name: str) -> None:
            if field_name not in track.manual_fields:
                track.manual_fields.append(field_name)

        if title is not None and title != track.tags.title:
            track.tags.title = title
            mark_manual("title")
        if artist is not None and artist != track.tags.artist:
            track.tags.artist = artist
            mark_manual("artist")
        if album is not None and album != track.tags.album:
            track.tags.album = album
            mark_manual("album")
        if year is not None:
            normalized_year = year if year else None
            if normalized_year != track.tags.year:
                track.tags.year = normalized_year
                mark_manual("year")
        if tag_genre is not None and tag_genre != track.tags.genre:
            track.tags.genre = tag_genre
            mark_manual("tag_genre")
            mapped = self.ontology.map_genre_value(tag_genre)
            if mapped:
                track.derived.genre = mapped
                track.derived.genre_source = "tag"
        if derived_genre is not None and derived_genre != track.derived.genre:
            track.derived.genre = derived_genre
            track.derived.genre_source = "manual" if derived_genre else ""
            mark_manual("derived_genre")
            if derived_genre:
                track.derived.content_type = "music"
        if derived_mood is not None and derived_mood != track.derived.mood:
            track.derived.mood = derived_mood
            mark_manual("derived_mood")
        if user_notes is not None:
            track.derived.user_notes = user_notes

        lyrics_changed = False
        if lyrics is not None and lyrics != track.derived.lyrics:
            lyrics_changed = True
            track.derived.lyrics = lyrics
            track.derived.lyrics_source = "manual" if lyrics.strip() else ""
            track.derived.lyrics_segments = []
            track.derived.has_vocal = bool(lyrics.strip())
            track.derived.enrich_status = "done"

        if lyrics_changed:
            if lyrics.strip():
                embedding = self.text_embedder.encode(lyrics, is_query=False)
                self.db.update_text(track.id, embedding)
            else:
                self.db.update_text(
                    track.id, np.zeros(self.db.text_dim, dtype="float32")
                )

        self.save()
        return track
