import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["PATH"] = r"C:\Users\Adli\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin" + os.pathsep + os.environ["PATH"]

import whisper
import time
import warnings
warnings.filterwarnings("ignore")

MODEL_SIZE = "base"
TEST_FILE = "data/ぼくらはみんな意味不明 (nu metal Remix) - PinocchioP.mp3"

print(f"Загрузка Whisper ({MODEL_SIZE})...")
t0 = time.time()
model = whisper.load_model(MODEL_SIZE)
print(f"  Загрузка: {time.time() - t0:.1f} сек")

print(f"\nРаспознавание: {Path(TEST_FILE).name}")
t0 = time.time()
result = model.transcribe(TEST_FILE, language=None)  # language=None → автоопределение
print(f"  Время: {time.time() - t0:.1f} сек")

print(f"  Определённый язык: {result['language']}")
print(f"\n  Распознанный текст:")
print(f"  {result['text'].strip()}")