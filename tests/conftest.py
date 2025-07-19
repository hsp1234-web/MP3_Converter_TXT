import pytest
import sqlite3
import sys
import os
import subprocess
import time
import httpx

# 將專案根目錄添加到 Python 路徑中
@pytest.fixture(scope="session", autouse=True)
def add_project_root_to_path():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

@pytest.fixture
def db_connection():
    """
    提供一個乾淨的、用於測試的 SQLite 資料庫連線。
    """
    from src.database import DATABASE_FILE, initialize_database

    if os.path.exists(DATABASE_FILE):
        os.remove(DATABASE_FILE)

    initialize_database()

    conn = sqlite3.connect(DATABASE_FILE)
    yield conn
    conn.close()

    if os.path.exists(DATABASE_FILE):
        os.remove(DATABASE_FILE)

@pytest.fixture(scope="session")
def live_api_server():
    """
    啟動並管理 API 伺服器的生命週期。
    """
    env = os.environ.copy()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"

    # 清理舊的日誌檔案
    if os.path.exists("api_server.log"):
        os.remove("api_server.log")

    with open("api_server.log", "w") as log_file:
        process = subprocess.Popen(
            [sys.executable, "-u", "src/main.py"],
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT
        )

    # 健康探針
    base_url = "http://127.0.0.1:8000"
    is_ready = False
    for _ in range(10): # 嘗試 10 次，共 10 秒
        try:
            with httpx.Client() as client:
                response = client.get(f"{base_url}/health")
            if response.status_code == 200:
                is_ready = True
                break
        except httpx.ConnectError:
            time.sleep(1)

    if not is_ready:
        process.terminate()
        with open("api_server.log", "r") as f:
            logs = f.read()
        pytest.fail(f"API 伺服器啟動失敗。日誌:\n{logs}")

    yield base_url

    process.terminate()

@pytest.fixture(scope="session")
def live_worker():
    """
    啟動並管理 Transcriber Worker 的生命週期。
    """
    env = os.environ.copy()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"
    process = subprocess.Popen([sys.executable, "-u", "src/transcriber_worker.py"], env=env)
    yield
    process.terminate()
