import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import time
import numpy as np
import torch
from transformers import ClapModel, ClapProcessor
from sentence_transformers import SentenceTransformer

print("=" * 60)
print("Проверка загрузки моделей на CPU")
print("=" * 60)

# ---------- CLAP ----------
print("\n[1/2] Загрузка CLAP...")
t0 = time.time()
clap_model = ClapModel.from_pretrained("laion/clap-htsat-unfused")
clap_processor = ClapProcessor.from_pretrained("laion/clap-htsat-unfused")
clap_model.eval()
print(f"    Загрузка: {time.time() - t0:.1f} сек")

# Проверим текстовую ветку CLAP
print("\n[2/2] Тест текстового запроса через CLAP...")
t0 = time.time()
inputs = clap_processor(text=["calm piano music"], return_tensors="pt")
with torch.no_grad():
    outputs = clap_model.get_text_features(**inputs)
    text_emb = outputs.pooler_output
print(f"    Инференс: {time.time() - t0:.2f} сек")
print(f"    Размерность эмбеддинга: {text_emb.shape}")

# ---------- MiniLM ----------
print("\n[3/3] Загрузка MiniLM...")
t0 = time.time()
minilm = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
print(f"    Загрузка: {time.time() - t0:.1f} сек")

t0 = time.time()
emb = minilm.encode("calm piano music")
print(f"    Инференс: {time.time() - t0:.3f} сек")
print(f"    Размерность эмбеддинга: {emb.shape}")

print("\n" + "=" * 60)
print("Все модели работают на CPU корректно.")
print("=" * 60)