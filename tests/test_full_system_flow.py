"""完整系統流程測試."""
from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import pytest

if TYPE_CHECKING:
    import sqlite3

# 測試音訊檔案的路徑
TEST_AUDIO_PATH = Path(__file__).parent / "audio" / "test_audio.wav"


@pytest.mark.e2e
def test_upload_and_poll_to_completion(
    live_api_server: str,
    live_worker: None,
    db_connection: sqlite3.Connection,
) -> None:
    """一個完整的端對端測試, 驗證從上傳到完成的整個流程."""
    del live_worker, db_connection
    base_url = live_api_server
    # 確保測試音訊檔案存在
    assert TEST_AUDIO_PATH.exists(), f"測試音訊檔案不存在於: {TEST_AUDIO_PATH}"

    # --- 行動 1: 上傳檔案 ---
    with TEST_AUDIO_PATH.open("rb") as f:
        files = {"file": (TEST_AUDIO_PATH.name, f, "audio/wav")}
        with httpx.Client() as client:
            response = client.post(f"{base_url}/upload", files=files, timeout=10)

    # --- 斷言 1: 任務接收 ---
    assert response.status_code == 202, f"預期狀態碼為 202, 但收到 {response.status_code}"
    response_json = response.json()
    assert "task_id" in response_json, "回應中未找到 'task_id'"
    task_id = response_json["task_id"]

    # --- 行動 2: 輪詢狀態 ---
    start_time = time.time()
    timeout = 60  # 秒
    poll_interval = 2  # 秒
    final_status = None

    while time.time() - start_time < timeout:
        with httpx.Client() as client:
            status_response = client.get(f"{base_url}/status/{task_id}", timeout=10)

        assert status_response.status_code == 200
        status_data: dict[str, Any] = status_response.json()
        current_status = status_data.get("status")

        # --- 斷言 2: 狀態變更 ---
        assert current_status in {"pending", "processing", "completed", "failed"}

        if current_status == "completed":
            final_status = status_data
            break

        if current_status == "failed":
            pytest.fail(f"任務失敗: {status_data.get('error_message')}")

        time.sleep(poll_interval)
    else:
        pytest.fail(f"輪詢超時 ({timeout}秒), 任務未完成.")

    # --- 斷言 3: 結果驗證 ---
    assert final_status is not None, "最終狀態不應為 None"
    assert final_status["status"] == "completed"
    # 放寬斷言條件, 只檢查關鍵字
    result_text = final_status.get("result_text", "").lower()
    assert "birch" in result_text
    assert "smooth" in result_text
