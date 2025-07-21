"""Pytest 設定檔案."""
import os
import aiosqlite
import subprocess
import sys
import time
from pathlib import Path
from typing import Generator

import httpx
import pytest

# 將專案根目錄添加到 Python 路徑中
@pytest.fixture(scope="session", autouse=True)
def add_project_root_to_path() -> None:
    """將專案根目錄添加到 Python 路徑中."""
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


@pytest.fixture
@pytest.mark.asyncio
async def db_connection() -> Generator[aiosqlite.Connection, None, None]:
    """提供一個乾淨的、用於測試的 SQLite 資料庫連線."""
    from src.core import DATABASE_FILE, initialize_database

    db_path = Path(DATABASE_FILE)
    if db_path.exists():
        db_path.unlink()

    await initialize_database()

    conn = await aiosqlite.connect(DATABASE_FILE)
    yield conn
    await conn.close()

    if db_path.exists():
        db_path.unlink()


@pytest.fixture(scope="session")
def live_api_server() -> Generator[str, None, None]:
    """啟動並管理 API 伺服器的生命週期."""
    env = os.environ.copy()
    project_root = Path(__file__).resolve().parent.parent
    env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"

    # 清理舊的日誌檔案
    log_path = Path("api_server.log")
    if log_path.exists():
        log_path.unlink()

    # 使用 uvicorn 啟動
    command = [
        "uvicorn",
        "src.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]

    with log_path.open("w") as log_file:
        process = subprocess.Popen(
            command,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

    # 健康探針
    base_url = "http://127.0.0.1:8000"
    is_ready = False
    for _ in range(10):  # 嘗試 10 次, 共 10 秒
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
        logs = log_path.read_text()
        pytest.fail(f"API 伺服器啟動失敗. 日誌:\n{logs}")

    try:
        yield base_url
    finally:
        process.terminate()
        process.wait(timeout=5)


# The live_worker fixture is no longer needed, as the lifespan manager
# now handles worker processes.
