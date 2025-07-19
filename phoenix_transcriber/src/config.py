import os

# --- 資料夾設定 ---
IN_DIR = "IN"
OUT_DIR = "OUT"
PROCESSED_DIR = os.path.join(IN_DIR, "_PROCESSED")

# --- AI 模型設定 ---
# 可在 "tiny", "base", "small", "medium", "large-v3" 中選擇
MODEL_SIZE = "mock"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"
