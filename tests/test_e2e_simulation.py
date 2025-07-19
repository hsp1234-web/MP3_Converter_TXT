# -*- coding: utf-8 -*-
"""
作戰代號：【單體迴路】

目標：驗證系統在一個受控的、單一進程環境下的核心邏輯。
此測試取代了舊的、基於外部行程的端到端模擬，以根除不確定性並提升執行效率。
"""
import pytest
import multiprocessing as mp
from fastapi.testclient import TestClient

# --- 核心作戰單位匯入 ---
# 1. 匯入 FastAPI 應用程式實例
from src.main import app
# 2. 匯入佇列的存取介面
from src.main import get_task_queue, get_result_queue, get_log_queue
# 3. 匯入單次執行的工人邏輯
from src.mock_worker import process_task_from_queue

# --- 測試環境設定 ---
@pytest.fixture(scope="function")
def client():
    """
    一個函式範圍的 pytest fixture，用於設定和清理測試環境。

    每次測試執行前：
    1. 建立全新的、乾淨的佇列。
    2. 將這些佇列注入到 FastAPI 應用程式中。
    3. 產生一個 TestClient 實例以供測試使用。
    """
    # 1. 建立新的佇列
    # 使用 "spawn" 方法以確保跨平台兼容性
    ctx = mp.get_context("spawn")
    task_q = ctx.Queue()
    result_q = ctx.Queue()
    log_q = ctx.Queue()

    # 2. 將佇列注入到 FastAPI 應用程式的全域變數中
    # 這是實現「單體迴路」的關鍵步驟
    from src import main
    main.task_queue = task_q
    main.result_queue = result_q
    main.log_queue = log_q

    # 3. 建立並返回 TestClient
    with TestClient(app) as test_client:
        yield test_client

    # 清理 (雖然在 "spawn" 模式下不是絕對必要，但良好實踐)
    task_q.close()
    result_q.close()
    log_q.close()


def test_monolithic_loop_paradigm(client: TestClient):
    """
    執行「單體迴路」測試範式。

    這個測試模擬了完整的任務生命週期，但完全在記憶體和單一進程中進行。
    """
    # --- 步驟 1: 透過 API 提交任務 ---
    # 使用 TestClient 模擬一個檔案上傳請求。
    # 這會觸發 `/upload` 端點，將一個新任務放入 `task_queue`。
    mock_audio_content = b"This is a mock audio file."
    response = client.post(
        "/upload",
        files={"file": ("test_audio.mp3", mock_audio_content, "audio/mpeg")}
    )

    # 驗證 API 回應是否符合預期
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "queued"
    job_id = response_data.get("job_id")
    assert job_id is not None
    print(f"✅ 步驟 1/3: 任務已成功提交，Job ID: {job_id}")

    # --- 步驟 2: 手動觸發工人邏輯 ---
    # 直接調用我們之前重構好的 `process_task_from_queue` 函數。
    # 這個函數會從 `task_queue` 中取出任務，進行處理，並將結果放入 `result_queue`。
    task_queue = get_task_queue()
    result_queue = get_result_queue()

    # 確認任務已在佇列中
    assert not task_queue.empty()

    # 執行單次處理循環
    process_task_from_queue(task_queue, result_queue)
    print("✅ 步驟 2/3: 工人核心邏輯已執行，任務已處理。")

    # --- 步驟 3: 從結果佇列驗證結果 ---
    # 由於我們在同一個進程中，可以直接從 `result_queue` 中獲取結果進行驗證。
    # 這種方法直接、可靠，且速度極快。
    assert not result_queue.empty()
    # 工人會先放入 "processing" 狀態，再放入 "completed" 狀態
    processing_result = result_queue.get(timeout=1)
    completed_result = result_queue.get(timeout=1)

    # 驗證 "processing" 狀態
    assert processing_result["status"] == "processing"
    assert processing_result["job_id"] == job_id

    # 驗證最終的 "completed" 狀態
    assert completed_result["status"] == "completed"
    assert completed_result["job_id"] == job_id
    assert "這是一個模擬的轉錄結果" in completed_result["transcript"]
    print("✅ 步驟 3/3: 結果已在結果佇列中成功驗證。")

    # 確認所有佇列都已處理完畢
    assert task_queue.empty()
    assert result_queue.empty()
    print("\n🎉 作戰成功：【單體迴路】測試驗證通過！")
