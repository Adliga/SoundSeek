import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["PATH"] = r"C:\Users\Adli\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin" + os.pathsep + os.environ["PATH"]

import whisper
import time
import warnings
warnings.filterwarnings("ignore")

# Путь к файлу, который создал Demucs
# Проверьте, как именно он называется у вас — vocals.wav или похоже
VOCALS_FILE = "data/separated/vocals.wav"

if not Path(VOCALS_FILE).exists():
    print(f"Файл не найден: {VOCALS_FILE}")
    print("Проверьте содержимое папки data/separated/")
    for f in Path("data/separated").rglob("*"):
        print(f"  {f}")
    exit(1)

print(f"Загрузка Whisper (base)...")
model = whisper.load_model("base")

print(f"\nРаспознавание отделённого вокала: {VOCALS_FILE}")
t0 = time.time()
result = model.transcribe(VOCALS_FILE, language=None)
print(f"  Время: {time.time() - t0:.1f} сек")
print(f"  Язык: {result['language']}")

print(f"\n--- Распознанный текст (на отделённом вокале) ---")
print(result['text'].strip())