"""硬體偵測模組."""
from __future__ import annotations

from typing import Any

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


def get_best_hardware_config() -> dict[str, Any]:
    """
    動態偵測硬體並返回最佳的 faster-whisper 設定.

    優先使用 CUDA, 其次是 CPU.
    如果 torch 不存在, 則直接使用 CPU.
    """
    if TORCH_AVAILABLE and torch.cuda.is_available():
        # 如果 CUDA 可用, 返回 GPU 的設定
        return {"device": "cuda", "compute_type": "float16"}
    if TORCH_AVAILABLE and torch.backends.mps.is_available():
        # Apple Silicon (MPS) 偵測
        return {"device": "mps", "compute_type": "float16"}

    # 否則, 返回 CPU 的設定
    return {"device": "cpu", "compute_type": "int8"}


if __name__ == "__main__":
    # 用於直接執行此腳本時的測試
    best_config = get_best_hardware_config()
