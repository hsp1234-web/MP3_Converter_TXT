import torch

def get_best_hardware_config():
    """
    偵測當前硬體並回傳最佳的 faster-whisper 設定。

    偵測邏輯:
    1. 優先偵測 NVIDIA CUDA。
    2. 其次偵測 AMD ROCm (目前未實作)。
    3. 再次偵測 Apple Silicon (MPS)。
    4. 最後默認為 CPU。

    Returns:
        dict: 包含 "device" 和 "compute_type" 的字典。
    """
    if torch.cuda.is_available():
        # TODO: 可以根據 GPU 型號選擇 int8_float16
        return {"device": "cuda", "compute_type": "float16"}

    # Apple Silicon (MPS) 偵測
    # 注意: faster-whisper 目前對 MPS 的支援可能不完整或效能不佳。
    # 這裡的實作是基於 torch 的通用 MPS 偵測。
    if torch.backends.mps.is_available():
        return {"device": "mps", "compute_type": "float16"} # 或者 "auto"

    # TODO: 偵測 AMD ROCm
    # 目前 faster-whisper 對 ROCm 的直接支援有限，
    # 通常需要透過 ROCm-enabled 的 PyTorch。
    # 這裡暫時跳過。

    # 如果沒有 GPU，則使用 CPU
    return {"device": "cpu", "compute_type": "int8"}

if __name__ == '__main__':
    # 用於直接執行此腳本時的測試
    config = get_best_hardware_config()
    print(f"偵測到的最佳硬體設定: {config}")
