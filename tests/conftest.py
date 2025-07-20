# tests/conftest.py
import os
import sys
import time
import pytest
import requests
import subprocess
from pathlib import Path

# --- 核心修復：手動設定子進程的 Python 路徑 ---
# 取得專案的根目錄 (即 conftest.py 所在目錄的上一層)
PROJECT_ROOT = Path(__file__).parent.parent

@pytest.fixture(scope="session")
def live_api_server():
    """
    啟動一個真實的 Uvicorn API 伺服器作為背景進程，用於 E2E 測試。
    這個 fixture 會在所有測試開始前啟動伺服器，並在結束後將其關閉。
    """
    # 複製當前的環境變數，這是確保子進程能找到 python 直譯器等工具的關鍵
    env = os.environ.copy()

    # 取得現有的 PYTHONPATH，如果不存在則為空字串
    python_path = env.get("PYTHONPATH", "")

    # 將專案根目錄添加到 PYTHONPATH 的最前端
    # 我們使用 os.pathsep 作為分隔符，以確保跨平台相容性 (Windows 是 ';', Linux 是 ':')
    env["PYTHONPATH"] = f"{PROJECT_ROOT}{os.pathsep}{python_path}"

    # 定義啟動 Uvicorn 的指令
    # 我們直接使用 sys.executable 來確保用的是與 pytest 相同的 Python 直譯器
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8001", # 使用一個不常用的埠，避免與手動執行的伺服器衝突
    ]

    # 使用 subprocess.Popen 啟動伺服器
    # 關鍵：傳入我們修改過的 env 環境變數
    server_process = subprocess.Popen(command, env=env)

    # --- 健康檢查 ---
    # 給予伺服器足夠的啟動時間，並進行健康檢查
    api_url = "http://127.0.0.1:8001"
    retries = 10 # 增加重試
    delay = 1
    for i in range(retries):
        try:
            response = requests.get(f"{api_url}/", timeout=1)
            if response.status_code == 200:
                print(f"\n✅ 測試伺服器已在 {api_url} 成功啟動。")
                break
        except requests.ConnectionError:
            time.sleep(delay)
    else:
        # 如果重試多次後仍然失敗，則終止進程並拋出錯誤
        server_process.terminate()
        pytest.fail(f"❌ 無法在 {retries * delay} 秒內連接到測試伺服器。")

    # 使用 yield 將 API URL 提供給測試函數
    yield api_url

    # --- 清理工作 ---
    # 所有測試執行完畢後，終止伺服器進程
    print("\n🛑 正在關閉測試伺服器...")
    server_process.terminate()
    server_process.wait()
    print("✅ 測試伺服器已關閉。")
