"""Единая конфигурация SoundSeek.

Все пути строятся от корня проекта, чтобы приложение и служебные скрипты
работали одинаково независимо от текущего каталога запуска.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
TRACKS_DIR = DATA_DIR / "tracks"
INDEXES_DIR = DATA_DIR / "indexes"
COVERS_DIR = DATA_DIR / "covers"
SEPARATED_DIR = DATA_DIR / "separated"
KNOWLEDGE_DIR = PROJECT_ROOT / "soundseek_core" / "knowledge"
ONTOLOGY_PATH = KNOWLEDGE_DIR / "ontology.json"
INDEX_PATH = INDEXES_DIR / "library"

# ---------- Аудио ----------
AUDIO_EXTENSIONS = (".mp3", ".wav", ".flac", ".ogg", ".m4a", ".opus", ".aac")
SAMPLE_RATE = 48_000
CLAP_WINDOW_SECONDS = 10  # CLAP-htsat-unfused обучен на 10-секундных окнах
# Мелодический канал по-прежнему использует средний фрагмент: один контур
# на весь длинный трек был бы слишком грубым для DTW.
INDEX_WINDOW_SECONDS = 30
INDEX_SEGMENTS = 3  # совместимость со старым API и тестами
# CLAP-эмбеддинг считается по окнам, распределённым по всему треку.
# Ограничение защищает от неконтролируемого времени на очень длинных файлах.
INDEX_MAX_WINDOWS = int(os.getenv("SOUNDSEEK_INDEX_MAX_WINDOWS", "72"))
QUERY_WINDOW_SECONDS = 30

# ---------- Модели ----------
CLAP_MODEL_NAME = os.getenv("SOUNDSEEK_CLAP_MODEL", "laion/clap-htsat-unfused")
# Мультиязычная модель нужна для русских текстов песен и запросов.
# Если она недоступна, TextEmbedder откатится на английскую MiniLM.
TEXT_MODEL_NAME = os.getenv(
    "SOUNDSEEK_TEXT_MODEL", "intfloat/multilingual-e5-small"
)
TEXT_MODEL_FALLBACK = "sentence-transformers/all-MiniLM-L6-v2"
TEXT_EMBEDDING_DIM = 384
AUDIO_EMBEDDING_DIM = 512
WHISPER_MODEL_SIZE = os.getenv("SOUNDSEEK_WHISPER_MODEL", "base")

# ---------- Индексация ----------
CONFIDENCE_THRESHOLD = 0.15
CONFIDENCE_MARGIN = 0.02
MIN_MUSIC_DURATION = 10.0
LONG_FORM_THRESHOLD = 60.0
MIN_LYRICS_LENGTH = 15
MIN_ENRICH_DURATION = 20.0
EXCLUDED_DIRS = {"separated", "__pycache__", ".git", "covers", "indexes"}
EXCLUDED_PREFIXES = ("vocals", "no_vocals")

# ---------- Поиск ----------
DEFAULT_TOP_K = 5
CANDIDATE_MULTIPLIER = 5
MIN_CLAP_SCORE = 0.16
MIN_TEXT_SCORE = 0.18
MIN_METADATA_SCORE = 0.25
MIN_RESULT_SCORE = 0.10
RRF_K = 60

# ---------- База ----------
DB_VERSION = 2
AUDIO_EMBEDDING_VERSION = 4
TEXT_EMBEDDING_VERSION = 2


def ensure_directories() -> None:
    for directory in (TRACKS_DIR, INDEXES_DIR, COVERS_DIR, SEPARATED_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def find_ffmpeg() -> str | None:
    """Ищет ffmpeg без привязки к конкретному пользователю Windows."""
    found = shutil.which("ffmpeg")
    if found:
        return str(Path(found).parent)

    candidates = [
        Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages",
        Path("C:/ffmpeg/bin"),
        Path("C:/Program Files/ffmpeg/bin"),
    ]
    for root in candidates:
        if not root.exists():
            continue
        for candidate in root.glob("**/ffmpeg.exe"):
            return str(candidate.parent)
    return None


def configure_runtime() -> None:
    """Настройки окружения, которые должны примениться до импорта моделей."""
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("DEMUCS_DEVICE", "cpu")
    ffmpeg_dir = find_ffmpeg()
    if ffmpeg_dir:
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")


configure_runtime()
