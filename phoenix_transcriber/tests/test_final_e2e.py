import subprocess
import time
import pytest
import httpx
import websockets
import asyncio
import os
import json

@pytest.fixture(scope="module")
def server():
    # 在背景啟動主應用程式
    process = subprocess.Popen(["poetry", "run", "python", "src/launcher.py"])
    time.sleep(15) # 等待伺服器和模型載入
    yield
    process.terminate()
    process.wait()

@pytest.mark.asyncio
async def test_full_transcription_flow(server):
    # 準備測試檔案
    test_file = "tests/test_audio.wav"
    assert os.path.exists(test_file)

    results = []
    # 設定 WebSocket 連線來接收結果
    async with websockets.connect("ws://localhost:8000/ws") as websocket:

        # 異步上傳檔案
        async with httpx.AsyncClient() as client:
            with open(test_file, "rb") as f:
                files = {'file': (os.path.basename(test_file), f, 'audio/wav')}
                response = await client.post("http://localhost:8000/upload", files=files, timeout=30)
                assert response.status_code == 200
                upload_result = response.json()
                assert "job_id" in upload_result

        # 等待並接收 WebSocket 訊息
        try:
            while True:
                message = await asyncio.wait_for(websocket.recv(), timeout=60)
                result = json.loads(message)
                if result.get("job_id") == upload_result["job_id"]:
                    results.append(result)
                    if result.get("status") == "completed" or result.get("status") == "error":
                        break
        except asyncio.TimeoutError:
            pytest.fail("WebSocket 在指定時間內未收到完成訊息")

    # 驗證收到的訊息序列
    assert len(results) >= 2, "應至少收到 queued 和 completed/error 訊息"
    statuses = [r.get("status") for r in results]
    assert "queued" in statuses
    assert "processing" in statuses
    assert "completed" in statuses, f"最終狀態不是 completed，收到的訊息: {results}"
