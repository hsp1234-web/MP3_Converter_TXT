"""端到端流程測試."""
import time
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from src.main import app

@pytest.mark.e2e
def test_full_transcription_flow_with_testclient(db_connection):
    """
    一個使用 TestClient 的完整端到端測試案例。
    """
    del db_connection  # 我們只需要 fixture 的副作用（初始化資料庫）
    with TestClient(app) as client:
        # lifespan startup is triggered here

        # --- Step 1: 上傳一個模擬音訊檔案 ---
        mock_audio_path = Path("test_audio.wav")
        mock_audio_path.write_bytes(
            b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80\xbb\x00\x00\x00\xee\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00"
        )

        with mock_audio_path.open("rb") as f:
            files = {"file": (mock_audio_path.name, f, "audio/wav")}
            response = client.post("/upload", files=files)

        assert response.status_code == 202
        task_id = response.json().get("task_id")
        assert task_id is not None

        # --- Step 2: 輪詢狀態 ---
        start_time = time.time()
        timeout = 20  # seconds
        final_status = None
        while time.time() - start_time < timeout:
            response = client.get(f"/status/{task_id}")
            assert response.status_code == 200
            status_data = response.json()
            # 因為 lifespan 啟動的是 mock_worker，它只會 sleep，不會更新資料庫
            # 所以我們預期狀態會一直保持 pending
            # 在這個測試中，我們的主要目標是驗證 API->Queue 的流程是通的
            if status_data.get("status") == "pending":
                final_status = status_data
                break
            time.sleep(1)

        assert final_status is not None, "任務狀態不是 pending"
        assert final_status["status"] == "pending"


        # --- Step 3: 清理 ---
        if mock_audio_path.exists():
            mock_audio_path.unlink()

    # lifespan shutdown is triggered here
