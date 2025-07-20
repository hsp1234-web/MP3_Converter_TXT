# src/model_state.py
from enum import Enum

class ModelStatus(Enum):
    """
    定義模型所有可能的狀態。
    """
    DOWNLOADING = "模型下載中"
    LOADING = "模型載入中"
    READY = "準備就緒"
    TRANSCRIBING = "轉錄中"
    ERROR = "發生錯誤"

# --- 全域狀態變數 ---
# 這些變數會在應用程式的不同部分共享，以追蹤模型的當前狀態。

# 模型實例，初始為 None
model_instance = None

# 當前狀態，初始為下載中
current_status: ModelStatus = ModelStatus.DOWNLOADING
