# commander_console.py

import sys
from pathlib import Path
import typer
import uvicorn
import subprocess
import os

# --- 根本性修復 ---
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))
# --- 修復結束 ---

cli = typer.Typer()

@cli.command()
def run_server(host: str = "127.0.0.1", port: int = 8000, profile: str = "testing"):
    """
    啟動 FastAPI 應用程式伺服器。
    """
    print(f"INFO:     啟動伺服器於 http://{host}:{port}，使用設定檔: {profile}")
    # 將設定檔傳遞給環境變數，以便應用程式在啟動時讀取
    os.environ["APP_PROFILE"] = profile
    uvicorn.run("src.main:app", host=host, port=port, reload=True)

@cli.command()
def run_tests(marker: str = None):
    """
    執行自動化測試。
    可以使用 -m 選項來選擇要執行的測試標記 (例如 "not e2e")。
    """
    print("==> 正在執行自動化測試...")
    test_env = os.environ.copy()
    test_env["PYTHONPATH"] = str(ROOT_DIR)

    command = ["python", "-m", "pytest", "-v"]
    if marker:
        command.extend(["-m", marker])

    try:
        subprocess.check_call(command, env=test_env)
        print("✅ 測試通過。")
    except subprocess.CalledProcessError as e:
        print(f"❌ 測試失敗: {e}")
        sys.exit(1)

@cli.command()
def db_init():
    """
    初始化資料庫。
    """
    from src.database import initialize_database
    print("正在初始化資料庫...")
    initialize_database()
    print("✅ 資料庫初始化完成。")

@cli.command()
def run_worker(profile: str = "testing"):
    """
    啟動轉寫工人行程。
    """
    from src.config import get_config
    from src.queues import task_queue, result_queue
    from src.transcriber_worker import transcriber_worker_process
    from src.logging_config import log_writer_process, get_logger
    import multiprocessing as mp

    print(f"INFO:     啟動工人，使用設定檔: {profile}")
    config = get_config(profile)

    # 建立日誌佇列
    log_queue = mp.Queue()

    # 啟動日誌寫入器
    log_process = mp.Process(target=log_writer_process, args=(log_queue,))
    log_process.start()

    # 啟動工人行程
    worker_process = mp.Process(
        target=transcriber_worker_process,
        args=(log_queue, task_queue, result_queue, config),
    )
    worker_process.start()

    print("✅ 工人行程已啟動。")
    worker_process.join()
    log_queue.put(None) # 傳送結束信號
    log_process.join()


@cli.command()
def clean():
    """
    清理專案中的快取檔案。
    """
    print("正在清理快取檔案...")
    for path in Path(".").rglob("__pycache__"):
        if path.is_dir():
            print(f"正在刪除: {path}")
            subprocess.run(["rm", "-rf", str(path)])
    for path in Path(".").glob(".pytest_cache"):
        if path.is_dir():
            print(f"正在刪除: {path}")
            subprocess.run(["rm", "-rf", str(path)])
    print("✅ 清理完成。")

if __name__ == "__main__":
    cli()
