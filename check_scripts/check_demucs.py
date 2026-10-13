import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import os
import time

# Используем CPU
os.environ["DEMUCS_DEVICE"] = "cpu"

from demucs_onnx import separate_stem

TEST_FILE = "data/lonely_day.mp3"
OUTPUT_DIR = "data/separated"

print(f"Загрузка Demucs и отделение вокала...")
t0 = time.time()

# separate_stem извлекает только одну дорожку (вокал)
# Это в ~4 раза быстрее, чем разделять на все 4 дорожки
vocals = separate_stem(TEST_FILE, stem="vocals", output_dir=OUTPUT_DIR)

print(f"  Время: {time.time() - t0:.1f} сек")
print(f"  Вокал сохранён в: {OUTPUT_DIR}/vocals.wav")