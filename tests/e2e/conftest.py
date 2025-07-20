# e2e/conftest.py
import os
import sys
import time
import pytest
import requests
import subprocess
from pathlib import Path

# 取得專案的根目錄
PROJECT_ROOT = Path(__file__).parent.parent

@pytest.fixture(scope="session")
def live_api_server():
    """
    啟動一個真實的 Uvicorn API 伺服器作為背景進程，用於 E2E 測試。
    這個 fixture 是 E2E 測試套件專用的，與單元測試完全分離。
    """
    # 這是最關鍵的一步：我們設定 PYTHONPATH，讓子進程知道專案的根在哪裡。
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    # 我們使用 `python -m uvicorn` 的標準方式來啟動，
    # 這會讓 Python 將 `src` 視為一個可導入的套件。
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8001",
    ]

    # 我們將所有輸出都重定向到一個日誌檔案中，以便調試
    with open("e2e_server.log", "w") as log_file:
        server_process = subprocess.Popen(command, env=env, stdout=log_file, stderr=subprocess.STDOUT)

    # --- 健康檢查 ---
    api_url = "http://127.0.0.1:8001"
    retries = 30  # 大幅增加重試次數，給模型下載和載入留出足夠時間
    delay = 1
    for i in range(retries):
        try:
            response = requests.get(f"{api_url}/", timeout=1)
            if response.status_code == 200:
                print(f"\n✅ E2E 伺服器已在 {api_url} 成功啟動。")
                break
        except requests.ConnectionError:
            time.sleep(delay)
    else:
        server_process.terminate()
        # 讀取日誌檔案以提供更多上下文
        log_content = Path("e2e_server.log").read_text()
        pytest.fail(f"❌ 無法在 {retries * delay} 秒內連接到 E2E 伺服器。\n伺服器日誌:\n{log_content}")

    yield api_url

    # --- 清理工作 ---
    print("\n🛑 正在關閉 E2E 伺服器...")
    server_process.terminate()
    server_process.wait()
    print("✅ E2E 伺服器已關閉。")
