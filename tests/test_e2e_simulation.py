import pytest
import time
import httpx
import websockets
import json
import asyncio
import os
import signal
import subprocess

# --- 測試設定 ---
BASE_URL = "http://localhost:8765"
WEBSOCKET_URL = "ws://localhost:8765/ws"
LOG_FILE = "phoenix_transcriber.log"

@pytest.fixture(scope="module")
def running_app():
    """
    在測試模組開始前，啟動應用程式；在結束後，終止它。
    """
    # 清理舊的日誌文件
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    # 在背景啟動應用程式
    # 使用 subprocess.Popen 以便我們可以獲取其 PID 並在之後終止它
    command = [".venv/bin/python", "src/launcher.py", "--profile", "testing"]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # 等待一段時間，確保伺服器有足夠的時間啟動
    time.sleep(5)

    # 檢查行程是否仍在運行
    assert process.poll() is None, "應用程式啟動失敗"

    yield process # 這將允許測試函數訪問 process 物件

    # --- 清理 ---
    print("\n正在終止應用程式...")
    # 向行程發送 SIGINT (Ctrl+C)
    process.send_signal(signal.SIGINT)
    try:
        # 等待行程終止
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        print("行程未能優雅關閉，將強制終止。")
        process.kill()

    # 打印剩餘的輸出以供調試
    stdout, stderr = process.communicate()
    print("\n--- 應用程式標準輸出 ---")
    print(stdout)
    print("\n--- 應用程式標準錯誤 ---")
    print(stderr)


async def test_full_e2e_simulation(running_app):
    """
    執行端到端的模擬測試。
    """
    job_id = None
    # 1. WebSocket 連線與訊息接收
    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            print("WebSocket 已連線")

            # 2. API 上傳請求
            async with httpx.AsyncClient() as client:
                # 建立一個模擬的音訊檔案
                mock_audio_content = b"mock_audio_data"
                files = {'file': ('test_audio.mp3', mock_audio_content, 'audio/mpeg')}

                # 發送上傳請求
                response = await client.post(f"{BASE_URL}/upload", files=files)
                assert response.status_code == 200
                print(f"API 回應: {response.json()}")
                job_id = response.json().get("job_id")
                assert job_id is not None

            # 3. 驗證 WebSocket 訊息
            expected_statuses = ["queued", "processing", "completed"]
            received_statuses = []

            # 設定一個超時
            timeout = 10  # 秒
            start_time = time.time()

            while len(received_statuses) < len(expected_statuses) and (time.time() - start_time) < timeout:
                try:
                    message_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    message = json.loads(message_str)
                    print(f"收到 WebSocket 訊息: {message}")

                    if message.get("job_id") == job_id:
                        status = message.get("status")
                        if status and status not in received_statuses:
                            received_statuses.append(status)

                except asyncio.TimeoutError:
                    continue # 如果一秒內沒收到訊息，繼續等待

            assert received_statuses == expected_statuses
            print("WebSocket 狀態驗證成功")

    except Exception as e:
        pytest.fail(f"測試過程中發生錯誤: {e}")

    # 4. 日誌系統驗證
    assert os.path.exists(LOG_FILE), "日誌檔案未被建立"

    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        log_content = f.read()

    print("\n--- 日誌檔案內容 ---")
    print(log_content)
    print("--------------------")

    assert "APIServerProcess" in log_content
    assert "API伺服器" in log_content
    assert "MockWorkerProcess" in log_content
    assert "模擬工人" in log_content
    assert "INFO" in log_content
    assert "鳳凰錄音轉寫服務" in log_content
    assert f"收到新任務: Job ID {job_id}" in log_content
    assert f"任務 {job_id}: 模擬處理完成" in log_content
    print("日誌系統驗證成功")
