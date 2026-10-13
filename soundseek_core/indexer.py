import os

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
from typing import Optional, List, Tuple
from transformers import ClapModel, ClapProcessor
from sentence_transformers import SentenceTransformer
from demucs_onnx import separate_stem

from .models import Track
from .db import VectorDB


SAMPLE_RATE = 48000
SEGMENT_SECONDS = 30
CLAP_MODEL_NAME = "laion/clap-htsat-unfused"
MINILM_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
WHISPER_MODEL_SIZE = "base"
AUDIO_EXTENSIONS = (".mp3", ".wav", ".flac", ".ogg", ".m4a")
MIN_LYRICS_LENGTH = 15
EXCLUDED_DIRS = {"separated", "__pycache__", ".git"}
EXCLUDED_PREFIXES = ("library", "vocals", "no_vocals")


class AudioIndexer:
    def __init__(self, db_path: Optional[str] = None, ontology=None):
        print("Загрузка CLAP...")
        self.clap_model = ClapModel.from_pretrained(CLAP_MODEL_NAME)
        self.clap_processor = ClapProcessor.from_pretrained(CLAP_MODEL_NAME)
        self.clap_model.eval()

        print("Загрузка MiniLM...")
        self.minilm = SentenceTransformer(MINILM_MODEL_NAME, device="cpu")

        self.whisper = None  # ленивая загрузка
        self.ontology = ontology

        self.db = VectorDB(audio_dim=512, text_dim=384)
        self.db_path = db_path
        if db_path and Path(f"{db_path}.audio.faiss").exists():
            self.db.load(db_path)
            print(f"Загружено {len(self.db)} треков из {db_path}")

    # ---------- Ленивая загрузка Whisper ----------
    def _get_whisper(self):
        if self.whisper is None:
            print(f"Загрузка Whisper ({WHISPER_MODEL_SIZE})...")
            self.whisper = whisper.load_model(WHISPER_MODEL_SIZE)
        return self.whisper

    # ---------- Аудио ----------
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

    # ---------- Zero-shot классификация ----------
    def classify_audio(self, audio_emb: np.ndarray, ontology) -> tuple:
        def _best(prompts: dict) -> str:
            if not prompts:
                return ""
            names = list(prompts.keys())
            texts = list(prompts.values())

            inputs = self.clap_processor(
                text=texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=77,
            )
            with torch.no_grad():
                outputs = self.clap_model.get_text_features(**inputs)
                text_embs = outputs.pooler_output if hasattr(outputs, "pooler_output") else outputs

            audio_t = torch.tensor(audio_emb).unsqueeze(0).float()
            audio_t = F.normalize(audio_t, dim=-1)
            text_embs = F.normalize(text_embs, dim=-1)

            sims = (audio_t @ text_embs.T).squeeze(0)
            best_idx = int(torch.argmax(sims))
            return names[best_idx]

        genre = _best(ontology.get_genre_prompts())
        mood = _best(ontology.get_mood_prompts())
        return genre, mood

    # ---------- Вокал и текст ----------
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

    # ---------- Сбор файлов ----------
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

    # ---------- ПРОХОД 1: лёгкая индексация ----------
    def index_file_light(self, path: str) -> Optional[Track]:
        track_id = Path(path).stem
        if self.db.contains(track_id):
            print(f"  пропуск (уже в базе): {Path(path).name}")
            return None

        t0 = time.time()
        audio = self._load_audio_segment(path)
        audio_emb = self.get_audio_embedding(audio)
        t_audio = time.time() - t0

        genre, mood = "", ""
        t_classify = 0.0
        if self.ontology is not None:
            t3 = time.time()
            genre, mood = self.classify_audio(audio_emb, self.ontology)
            t_classify = time.time() - t3

        track = Track(
            id=track_id,
            path=str(Path(path).resolve()),
            duration=librosa.get_duration(path=path),
            genre=genre,
            mood=mood,
        )
        self.db.add(audio_emb, track, text_embedding=None)

        total = time.time() - t0
        print(
            f"  [{total:.1f} сек: audio {t_audio:.1f} + classify {t_classify:.1f}] "
            f"{genre}/{mood} | {Path(path).name}"
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

    # ---------- ПРОХОД 2: обогащение текстом ----------
    def enrich_with_lyrics(self, max_tracks: Optional[int] = None) -> int:
        targets = [t for t in self.db.tracks if not t.lyrics]
        if max_tracks:
            targets = targets[:max_tracks]

        print(f"Треков для обогащения: {len(targets)}")
        for i, track in enumerate(targets, 1):
            print(f"[{i}/{len(targets)}] {track.id}")

            t0 = time.time()
            lyrics = ""
            text_emb = None
            t_demucs = t_whisper = 0.0

            with tempfile.TemporaryDirectory() as tmp_dir:
                t1 = time.time()
                vocals_path = self._separate_vocals(track.path, tmp_dir)
                t_demucs = time.time() - t1

                if vocals_path:
                    t2 = time.time()
                    lyrics = self._transcribe(vocals_path)
                    t_whisper = time.time() - t2

            if len(lyrics) >= MIN_LYRICS_LENGTH:
                track.lyrics = lyrics
                track.has_vocal = True
                text_emb = self.get_text_embedding(lyrics)
                self.db.update_text(track.id, text_emb)
            else:
                track.has_vocal = False

            total = time.time() - t0
            vocal_flag = "вокал" if track.has_vocal else "инстр."
            print(
                f"  [{total:.1f} сек: demucs {t_demucs:.1f} + whisper {t_whisper:.1f}] "
                f"{vocal_flag}"
            )

            if self.db_path:
                self.db.save(self.db_path)

        return len(targets)
  