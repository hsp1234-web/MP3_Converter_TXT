import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.main import app  # 直接導入 FastAPI app
from src.transcriber_worker import transcriber_worker_process # 導入工人邏輯
from src.queues import task_queue, result_queue # 導入共享隊列
import json
import asyncio

# 使用 FastAPI 的 TestClient，它會在測試過程中管理 app 的生命週期
client = TestClient(app)

@pytest.mark.asyncio
async def test_single_loop_transcription_flow():
    """
    單體迴路測試：
    1. 透過 TestClient 提交任務到 API。
    2. 從 task_queue 中手動取出任務。
    3. 直接調用工人函數來處理該任務。
    4. 從 result_queue 中驗證處理結果。
    5. 透過 WebSocket (可選) 或 API 端點驗證最終狀態。
    """
    # 清空隊列，確保測試隔離
    while not task_queue.empty():
        task_queue.get_nowait()
    while not result_queue.empty():
        result_queue.get_nowait()

    # --- 步驟 1: 透過 API 提交任務 ---
    test_file_path = "phoenix_transcriber/tests/test_audio.wav"
    assert os.path.exists(test_file_path), "測試音檔不存在"

    with open(test_file_path, "rb") as f:
        files = {'file': ('test_audio.wav', f, 'audio/wav')}
        response = client.post("/upload", files=files)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "queued"
    job_id = response_data["job_id"]

    # --- 步驟 2: 從佇列中手動取出任務 ---
    task = await task_queue.get()
    assert task is not None
    assert task["job_id"] == job_id

    # --- 步驟 3: 直接調用工人函數 ---
    # 在同一個事件循環中運行工人
    await process_task(task)

    # --- 步驟 4: 從結果佇列中驗證處理結果 ---
    result = await result_queue.get()
    assert result is not None
    assert result["job_id"] == job_id
    assert result["status"] == "completed"
    assert "transcript" in result
    print(f"轉錄結果: {result['transcript']}")

    # --- 步驟 5: (可選) 驗證 API 狀態 ---
    # 這裡我們需要一個方法來讓 API 知道結果，在真實應用中這是由工人進程完成的
    # 在這個測試中，我們可以模擬這個過程，或者直接檢查數據庫 (如果有的話)
    # 為了簡化，我們主要依賴隊列的結果

    print("單體迴路測試成功！")
