import pytest
import asyncio
import httpx
import websockets
import subprocess
import time
import os

# --- 常數設定 ---
BASE_URL = "http://127.0.0.1:8765"
WEBSOCKET_URL = "ws://127.0.0.1:8765/ws"
TEST_TIMEOUT = 40  # 整個測試的總超時時間（秒）
STARTUP_TIMEOUT = 30 # 應用程式啟動的超時時間（秒）

# --- Fixture: 管理應用程式的啟動與關閉 ---
@pytest.fixture(scope="module")
def app_process():
    """
    一個 Pytest Fixture，負責在測試開始前啟動應用程式，
    並在測試結束後將其關閉。
    'scope="module"' 表示這個 fixture 對於整個測試檔案只會執行一次。
    """
    process = None
    log_file = None
    try:
        # 使用 subprocess.Popen 啟動 launcher.py
        # 這比 Process 更能模擬真實的命令列啟動方式
        # 將日誌輸出到檔案中，方便除錯
        log_file = open("app_test.log", "w")
        cmd = ["poetry", "run", "python", "src/launcher.py"]

        # 使用 os.setsid 建立一個新的會話，這樣我們可以輕易地殺死整個行程樹
        process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, preexec_fn=os.setsid)

        # --- 等待應用程式完全啟動 ---
        # 這是測試中最關鍵也最脆弱的部分。我們需要一個可靠的方式來確認服務已就緒。
        # 策略：在超時時間內，持續嘗試用 httpx 連線到根 URL。
        start_time = time.time()
        while time.time() - start_time < STARTUP_TIMEOUT:
            try:
                with httpx.Client() as client:
                    # 我們不直接請求'/'，因為它被掛載為靜態目錄，可能會在uvicorn啟動但FastAPI應用未完全就緒時返回404。
                    # 嘗試一個不會被掛載覆蓋的已知API路徑，即使它不存在，能收到404也表示HTTP伺服器在回應。
                    # 或者，就像我們這裡做的，等待直到'/'返回200。
                    response = client.get(BASE_URL + "/")
                    if response.status_code == 200:
                        print(f"\n應用程式在 {time.time() - start_time:.2f} 秒後成功啟動。")
                        break
            except httpx.ConnectError:
                time.sleep(0.5) # 如果連線失敗，稍等一下再重試
        else:
            # 如果循環正常結束（即超時），則拋出錯誤
            pytest.fail(f"應用程式未能在 {STARTUP_TIMEOUT} 秒內啟動。請檢查 app_test.log。")

        # 使用 yield 將控制權交給測試函式
        yield process

    finally:
        # --- 測試結束後的清理工作 ---
        print("\n測試結束，正在關閉應用程式...")
        if process:
            # 使用 os.killpg 來殺死整個行程組，確保 uvicorn 和 worker 都被關閉
            import signal
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            try:
                # 等待行程終止
                process.wait(timeout=5)
                print("應用程式已成功關閉。")
            except subprocess.TimeoutExpired:
                print("關閉超時，強制終止。")
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        if log_file:
            log_file.close()
            with open("app_test.log", "r") as f:
                print("--- 應用程式日誌 ---")
                print(f.read())
                print("--------------------")


import json

# --- 測試函式 ---
def test_full_transcription_flow(app_process):
    """
    一個完整的端對端測試案例。
    1. 上傳檔案
    2. 連線 WebSocket
    3. 接收進度與結果訊息
    """
    async def run_test_logic():
        try:
            # --- 步驟 1: 上傳一個模擬音檔 ---
            async with httpx.AsyncClient(timeout=10) as client:
                mock_audio_content = b"dummy audio data"
                files = {'file': ('test_audio.mp3', mock_audio_content, 'audio/mpeg')}

                print("\n步驟 1: 正在上傳模擬音檔...")
                response = await client.post(f"{BASE_URL}/upload", files=files)

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["status"] == "processing"
                assert "job_id" in response_data
                job_id = response_data["job_id"]
                print(f"檔案上傳成功，後端已開始處理，任務 ID: {job_id}")

            # --- 步驟 2 & 3: 連線 WebSocket 並接收訊息 ---
            print("\n步驟 2: 正在連線 WebSocket...")
            received_messages = []

            async with asyncio.timeout(TEST_TIMEOUT):
                async with websockets.connect(WEBSOCKET_URL) as websocket:
                    print("WebSocket 連線成功。")

                    while True:
                        message_str = await websocket.recv()
                        message = json.loads(message_str)
                        print(f"收到訊息: {message}")

                        if message.get("job_id") == job_id:
                            received_messages.append(message)
                            if message.get("status") in ["completed", "error"]:
                                break

            print("\n步驟 3: 驗證收到的訊息...")
            assert len(received_messages) > 0, "沒有收到任何與此任務相關的 WebSocket 訊息"

            final_message = received_messages[-1]
            assert final_message["status"] in ["completed", "error"], f"最終訊息的狀態不是 'completed' 或 'error'，而是 '{final_message['status']}'"

            if final_message["status"] == "completed":
                assert "transcript" in final_message
                assert isinstance(final_message["transcript"], str)
                print(f"收到的轉錄結果: '{final_message['transcript']}'")
            else: # status is 'error'
                assert "message" in final_message
                print(f"收到預期中的錯誤訊息: {final_message['message']}")

            print("\n端對端流程驗證成功！")

        except asyncio.TimeoutError:
            pytest.fail(f"測試在 {TEST_TIMEOUT} 秒後超時。收到的訊息: {received_messages}")

    asyncio.run(run_test_logic())
