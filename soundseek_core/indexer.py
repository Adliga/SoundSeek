import os
import re

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["DEMUCS_DEVICE"] = "cpu"
os.environ["PATH"] = r"C:\Users\Adli\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin" + os.pathsep + os.environ["PATH"]

import time
import tempfile
import numpy as np
import librosa
import torch
import torch.nn.functional as F
import whisper
from pathlib import Path
from typing import Optional, List, Tuple, Callable
from transformers import ClapModel, ClapProcessor
from sentence_transformers import SentenceTransformer
from demucs_onnx import separate_stem

from .models import Track, FileTags, DerivedData
from .db import VectorDB


SAMPLE_RATE = 48000
SEGMENT_SECONDS = 30
CLAP_MODEL_NAME = "laion/clap-htsat-unfused"
MINILM_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
WHISPER_MODEL_SIZE = "base"
AUDIO_EXTENSIONS = (".mp3", ".wav", ".flac", ".ogg", ".m4a")
MIN_LYRICS_LENGTH = 15
EXCLUDED_DIRS = {"separated", "__pycache__", ".git", "covers", "indexes"}
EXCLUDED_PREFIXES = ("library", "vocals", "no_vocals")

CONFIDENCE_THRESHOLD = 0.15
MIN_MUSIC_DURATION = 10.0


class AudioIndexer:
    def __init__(self, db_path: Optional[str] = None, ontology=None):
        print("Загрузка CLAP...")
        self.clap_model = ClapModel.from_pretrained(CLAP_MODEL_NAME)
        self.clap_processor = ClapProcessor.from_pretrained(CLAP_MODEL_NAME)
        self.clap_model.eval()

        print("Загрузка MiniLM...")
        self.minilm = SentenceTransformer(MINILM_MODEL_NAME, device="cpu")

        self.whisper = None
        self.ontology = ontology

        self.db = VectorDB(audio_dim=512, text_dim=384)
        self.db_path = db_path
        if db_path and Path(f"{db_path}.audio.faiss").exists():
            self.db.load(db_path)
            print(f"Загружено {len(self.db)} треков из {db_path}")

    def _get_whisper(self):
        if self.whisper is None:
            print(f"Загрузка Whisper ({WHISPER_MODEL_SIZE})...")
            self.whisper = whisper.load_model(WHISPER_MODEL_SIZE)
        return self.whisper

    def _load_audio_segment(self, path: str) -> np.ndarray:
        duration = librosa.get_duration(path=path)
        if duration > SEGMENT_SECONDS:
            start = (duration - SEGMENT_SECONDS) / 2
            audio, _ = librosa.load(
                path, sr=SAMPLE_RATE, offset=start,
                duration=SEGMENT_SECONDS, mono=True,
            )
        else:
            audio, _ = librosa.load(path, sr=SAMPLE_RATE, mono=True)
        return audio

    def get_audio_embedding(self, audio: np.ndarray) -> np.ndarray:
        inputs = self.clap_processor(audio=audio, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        with torch.no_grad():
            outputs = self.clap_model.get_audio_features(**inputs)
            emb = outputs.pooler_output if hasattr(outputs, "pooler_output") else outputs
        return emb.numpy().flatten()

    def get_text_embedding(self, text: str) -> np.ndarray:
        return self.minilm.encode(text, convert_to_numpy=True)

    def get_query_text_embedding(self, text: str) -> np.ndarray:
        inputs = self.clap_processor(text=[text], return_tensors="pt")
        with torch.no_grad():
            outputs = self.clap_model.get_text_features(**inputs)
            emb = outputs.pooler_output if hasattr(outputs, "pooler_output") else outputs
        return emb.numpy().flatten()

    def _best_prompt(self, audio_emb: np.ndarray, prompts: dict,
                     threshold: float = CONFIDENCE_THRESHOLD) -> tuple:
        if not prompts:
            return "unknown", 0.0

        names = list(prompts.keys())
        texts = list(prompts.values())

        inputs = self.clap_processor(
            text=texts, return_tensors="pt",
            padding=True, truncation=True, max_length=77,
        )
        with torch.no_grad():
            outputs = self.clap_model.get_text_features(**inputs)
            text_embs = outputs.pooler_output if hasattr(outputs, "pooler_output") else outputs

        audio_t = torch.tensor(audio_emb).unsqueeze(0).float()
        audio_t = F.normalize(audio_t, dim=-1)
        text_embs = F.normalize(text_embs, dim=-1)

        sims = (audio_t @ text_embs.T).squeeze(0)
        best_idx = int(torch.argmax(sims))
        best_score = float(sims[best_idx])

        if best_score < threshold:
            return "unknown", best_score
        return names[best_idx], best_score

    def _map_tag_genre(self, tag_value: str, ontology) -> str:
        if not tag_value:
            return ""
        tokens = re.split(r"[;,/]", tag_value.lower())
        candidates = []
        for token in tokens:
            token = token.strip()
            concept = ontology._keyword_to_concept.get(token)
            if concept and concept in ontology.genres:
                candidates.append(concept)
        if not candidates:
            return ""
        for c in candidates:
            if ontology.genres[c].get("parent"):
                return c
        return candidates[0]

    def classify_audio(self, audio_emb, ontology, duration: float = 0.0,
                       tag_genre: str = "", filename: str = "") -> dict:
        result = {
            "content_type": "unknown",
            "genre": "",
            "mood": "",
            "confidences": {},
            "genre_source": "",
        }

        ct, ct_score = self._best_prompt(audio_emb, ontology.get_content_type_prompts())
        result["confidences"]["content_type"] = round(ct_score, 3)
        if ct == "unknown" and duration > MIN_MUSIC_DURATION:
            ct = "music"
        result["content_type"] = ct

        if ct != "music":
            return result

        all_leaves = ontology.get_all_leaf_prompts()
        clap_genre, g_score = self._best_prompt(audio_emb, all_leaves)
        result["confidences"]["genre_clap"] = round(g_score, 3)

        filename_genre = ""
        if filename:
            fn_concepts = ontology.extract_concepts(filename)
            if fn_concepts["genres"]:
                filename_genre = fn_concepts["genres"][0]

        tag_mapped = self._map_tag_genre(tag_genre, ontology)

        if tag_mapped:
            result["genre"] = tag_mapped
            result["genre_source"] = "tag"
            if clap_genre != "unknown" and not ontology.is_genre_related(tag_mapped, clap_genre):
                result["confidences"]["genre_conflict"] = f"tag={tag_mapped} vs clap={clap_genre}"
        elif filename_genre:
            result["genre"] = filename_genre
            result["genre_source"] = "filename"
            if clap_genre != "unknown" and not ontology.is_genre_related(filename_genre, clap_genre):
                result["confidences"]["genre_conflict"] = f"file={filename_genre} vs clap={clap_genre}"
        elif clap_genre != "unknown":
            result["genre"] = clap_genre
            result["genre_source"] = "clap"

        mood, m_score = self._best_prompt(audio_emb, ontology.get_mood_prompts())
        result["mood"] = "" if mood == "unknown" else mood
        result["confidences"]["mood"] = round(m_score, 3)

        return result

    def _separate_vocals(self, path: str, tmp_dir: str) -> Optional[str]:
        try:
            separate_stem(path, stem="vocals", output_dir=tmp_dir)
            vocals_path = Path(tmp_dir) / "vocals.wav"
            if vocals_path.exists():
                return str(vocals_path)
            return None
        except Exception as e:
            print(f"    Demucs ошибка: {e}")
            return None

    def _transcribe(self, audio_path: str) -> str:
        try:
            model = self._get_whisper()
            result = model.transcribe(audio_path, language=None, fp16=False)
            return result["text"].strip()
        except Exception as e:
            print(f"    Whisper ошибка: {e}")
            return ""

    def _collect_audio_files(self, folder: Path) -> list:
        files = []
        for f in folder.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            if any(part in EXCLUDED_DIRS for part in f.parts):
                continue
            if f.name.lower().startswith(EXCLUDED_PREFIXES):
                continue
            files.append(f)
        return files

    def index_file_light(self, path: str) -> Optional[Track]:
        track_id = Path(path).stem
        if self.db.contains(track_id):
            print(f"  пропуск (уже в базе): {Path(path).name}")
            return None

        t0 = time.time()
        audio = self._load_audio_segment(path)
        audio_emb = self.get_audio_embedding(audio)
        t_audio = time.time() - t0

        from .tags import read_tags, extract_cover
        raw_tags = read_tags(path)
        covers_dir = Path("data/covers")
        cover_path = extract_cover(path, track_id, covers_dir)

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

        duration = librosa.get_duration(path=path)

        classification = {"content_type": "unknown", "genre": "", "mood": "", "confidences": {}}
        t_classify = 0.0
        if self.ontology is not None:
            t3 = time.time()
            classification = self.classify_audio(
                audio_emb, self.ontology,
                duration=duration,
                tag_genre=tags.genre,
                filename=Path(path).name,
            )
            t_classify = time.time() - t3

        derived = DerivedData(
            content_type=classification["content_type"],
            genre=classification["genre"],
            mood=classification["mood"],
            duration=duration,
        )

        track = Track(id=track_id, path=str(Path(path).resolve()), tags=tags, derived=derived)
        self.db.add(audio_emb, track, text_embedding=None)

        total = time.time() - t0
        title_display = (tags.title or track_id)[:40]
        conf = classification["confidences"]
        conf_str = f"ct={conf.get('content_type', 0)}" if conf else ""
        source = classification.get("genre_source", "")
        source_str = f"[{source}]" if source else ""
        print(
            f"  [{total:.1f} сек: audio {t_audio:.1f} + classify {t_classify:.1f}] "
            f"{derived.content_type}/{derived.genre or '—'}/{derived.mood or '—'} "
            f"({conf_str}) {source_str} | {title_display}"
        )
        return track

    def index_folder_light(self, folder: str) -> int:
        folder = Path(folder).resolve()
        files = self._collect_audio_files(folder)
        print(f"Найдено файлов: {len(files)}")
        for i, f in enumerate(files, 1):
            print(f"[{i}/{len(files)}]", end=" ")
            try:
                self.index_file_light(str(f))
                if self.db_path:
                    self.db.save(self.db_path)
            except Exception as e:
                print(f"  Ошибка при обработке {f.name}: {e}")
        if self.db_path:
            print(f"База сохранена: {self.db_path}")
        return len(files)

    def reset_db(self):
        import faiss
        self.db.audio_index = faiss.IndexFlatIP(self.db.audio_dim)
        self.db.text_index = faiss.IndexFlatIP(self.db.text_dim)
        self.db.tracks = []
        self.db.ids = set()
        self.db.text_embeddings = []
        print("База сброшена.")

    def enrich_single_track(self, track: Track) -> bool:
        t0 = time.time()
        lyrics = ""

        with tempfile.TemporaryDirectory() as tmp_dir:
            vocals_path = self._separate_vocals(track.path, tmp_dir)
            if vocals_path:
                lyrics = self._transcribe(vocals_path)

        if len(lyrics) >= MIN_LYRICS_LENGTH:
            track.derived.lyrics = lyrics
            track.derived.has_vocal = True
            text_emb = self.get_text_embedding(lyrics)
            self.db.update_text(track.id, text_emb)
        else:
            track.derived.has_vocal = False
            track.derived.lyrics = ""

        if self.db_path:
            self.db.save(self.db_path)

        elapsed = time.time() - t0
        vocal_flag = "вокал" if track.derived.has_vocal else "инстр."
        print(f"  [{elapsed:.1f} сек] {vocal_flag} | {track.id}")

        return track.derived.has_vocal

    def enrich_with_lyrics(self, max_tracks: Optional[int] = None,
                           on_progress: Optional[Callable[[int, int, str], None]] = None) -> int:
        targets = [t for t in self.db.tracks if not t.derived.lyrics]
        if max_tracks:
            targets = targets[:max_tracks]

        total = len(targets)
        print(f"Треков для обогащения: {total}")
        for i, track in enumerate(targets, 1):
            print(f"[{i}/{total}] {track.id}", end=" ")
            try:
                self.enrich_single_track(track)
            except Exception as e:
                print(f"  Ошибка: {e}")

            if on_progress:
                try:
                    on_progress(i, total, track.id)
                except Exception:
                    pass

        return total

    # ---------- Ручное редактирование метаданных ----------
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
        """Обновляет поля трека. При изменении lyrics пересчитывает текстовый эмбеддинг."""
        track = next((t for t in self.db.tracks if t.id == track_id), None)
        if not track:
            return None

        if title is not None:
            track.tags.title = title
        if artist is not None:
            track.tags.artist = artist
        if album is not None:
            track.tags.album = album
        if year is not None:
            track.tags.year = year if year else None
        if tag_genre is not None:
            track.tags.genre = tag_genre
        if derived_genre is not None:
            track.derived.genre = derived_genre
            if derived_genre:
                track.derived.content_type = "music"
        if derived_mood is not None:
            track.derived.mood = derived_mood
        if user_notes is not None:
            track.derived.user_notes = user_notes

        lyrics_changed = False
        if lyrics is not None and lyrics != track.derived.lyrics:
            lyrics_changed = True
            track.derived.lyrics = lyrics
            track.derived.has_vocal = bool(lyrics.strip())

        if lyrics_changed:
            if lyrics.strip():
                text_emb = self.get_text_embedding(lyrics)
                self.db.update_text(track.id, text_emb)
            else:
                self.db.update_text(track.id, np.zeros(self.db.text_dim, dtype="float32"))

        if self.db_path:
            self.db.save(self.db_path)

        return track