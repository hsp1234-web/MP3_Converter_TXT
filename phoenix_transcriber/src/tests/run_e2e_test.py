import asyncio
import httpx
import websockets
import subprocess
import time
import os
import sys
import json

# --- 常數設定 ---
BASE_URL = "http://127.0.0.1:8000"
WEBSOCKET_URL = "ws://127.0.0.1:8000/ws"
TEST_TIMEOUT = 20
STARTUP_TIMEOUT = 15
LOG_FILE = "app_test.log"

async def run_test():
    """
    一個獨立的端對端測試函式。
    """
    process = None
    log_file_handle = None
    try:
        # --- 啟動應用程式 ---
        print("--- 步驟 1: 啟動應用程式 ---")
        log_file_handle = open(LOG_FILE, "w")
        # 注意：我們需要從專案的根目錄執行 launcher.py，所以路徑是 'src/launcher.py'
        cmd = ["poetry", "run", "python", "src/launcher.py"]

        # 在 poetry run 的上下文中，當前目錄就是專案根目錄
        process = subprocess.Popen(
            cmd,
            stdout=log_file_handle,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid  # 建立新的行程組，方便之後整個終止
        )

        # --- 等待服務就緒 ---
        print(f"等待應用程式啟動... (最多 {STARTUP_TIMEOUT} 秒)")
        start_time = time.time()
        app_ready = False
        while time.time() - start_time < STARTUP_TIMEOUT:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(BASE_URL + "/", timeout=2)
                    if response.status_code == 200:
                        print(f"應用程式在 {time.time() - start_time:.2f} 秒後成功啟動。")
                        app_ready = True
                        break
            except httpx.RequestError:
                await asyncio.sleep(0.5)

        if not app_ready:
            raise RuntimeError(f"應用程式未能在 {STARTUP_TIMEOUT} 秒內啟動。")

        # --- 執行測試流程 ---
        print("\n--- 步驟 2: 執行端對端測試流程 ---")

        # 步驟 2a: 上傳檔案
        async with httpx.AsyncClient(timeout=10) as client:
            mock_audio_content = b"this is a fake audio file for testing"
            files = {'file': ('e2e_test.mp3', mock_audio_content, 'audio/mpeg')}
            print("正在上傳模擬音檔...")
            response = await client.post(f"{BASE_URL}/upload", files=files)
            assert response.status_code == 200, f"上傳失敗，狀態碼: {response.status_code}"
            assert response.json()["status"] == "processing"
            print("檔案上傳成功，後端已開始處理。")

        # 步驟 2b: 連線 WebSocket 並接收所有訊息
        print("正在連線 WebSocket 並等待結果...")
        received_messages = []
        async with asyncio.timeout(TEST_TIMEOUT):
            async with websockets.connect(WEBSOCKET_URL) as websocket:
                print("WebSocket 連線成功。")
                while True:
                    message_str = await websocket.recv()
                    message = json.loads(message_str)
                    print(f"收到訊息: {message}")
                    received_messages.append(message)
                    if message.get("type") == "result":
                        print("已收到最終結果。")
                        break

        # --- 驗證結果 ---
        print("\n--- 步驟 3: 驗證接收到的訊息 ---")
        assert len(received_messages) > 0, "沒有收到任何 WebSocket 訊息"

        message_types = [msg.get("type") for msg in received_messages]
        assert "result" in message_types, "訊息流中缺少 'result' 訊息"

        final_message = received_messages[-1]
        assert final_message["type"] == "result", "最後一條訊息不是 'result' 類型"
        assert "transcript" in final_message, "結果訊息中缺少 'transcript' 欄位"
        assert "e2e_test.mp3" in final_message["transcript"], "轉寫結果中未包含檔名"

        print("所有訊息驗證成功！")
        print("\n--- ✅ 測試通過 ---")
        return True

    except Exception as e:
        print(f"\n--- ❌ 測試失敗: {e} ---", file=sys.stderr)
        # exc_info=True 會在日誌中印出完整的 traceback
        import logging
        logging.basicConfig(level=logging.ERROR)
        logging.error("測試執行期間發生錯誤", exc_info=True)
        return False

    finally:
        # --- 清理 ---
        print("\n--- 步驟 4: 清理 ---")
        if process:
            import signal
            print(f"正在終止應用程式行程組 (PGID: {os.getpgid(process.pid)})...")
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
                print("應用程式已成功關閉。")
            except (ProcessLookupError, subprocess.TimeoutExpired) as err:
                print(f"無法正常關閉，將強制終止: {err}")
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        if log_file_handle:
            log_file_handle.close()
            print(f"測試日誌已儲存至 {LOG_FILE}")
            # 印出日誌內容以供檢視
            with open(LOG_FILE, "r") as f:
                print("--- 應用程式日誌 ---")
                print(f.read())
                print("--------------------")

if __name__ == "__main__":
    # 執行測試並根據結果設定退出碼
    # 我們需要改變當前目錄，讓 `poetry run` 能找到 `pyproject.toml`
    # 這個腳本本身在 src/tests/ 裡面，所以我們要回到專案根目錄
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.chdir(project_root)
    print(f"已將工作目錄更改為: {os.getcwd()}")

    # 使用 asyncio.run 來執行我們的非同步主函式
    success = asyncio.run(run_test())

    if success:
        sys.exit(0)
    else:
        sys.exit(1)
