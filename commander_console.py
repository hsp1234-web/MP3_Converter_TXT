import click
import os
import sys
import subprocess

# --- 確保 src 目錄在 Python 路徑中 ---
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# --- 主命令群組 ---
@click.group()
def cli():
    """
    鳳凰錄音轉寫服務 - 統一指揮控制台。
    這是專案所有後台任務、數據處理和服務啟動的唯一入口。
    """
    pass

# --- 整合 launcher.py 的邏輯 ---
import time
import uvicorn
import multiprocessing as mp

# 由於我們已經將 src 加入 sys.path，可以直接從 src 導入
from src.main import app
from src.core import get_config
from src.transcriber_worker import transcriber_worker_process
from src.mock_worker import mock_worker_process
from src.core import get_logger, log_writer_process

def start_api_server(log_queue: mp.Queue, task_queue: mp.Queue, result_queue: mp.Queue, config):
    """
    啟動 FastAPI (Uvicorn) 伺服器。
    此函數在一個獨立的子行程中執行。
    """
    logger = get_logger("API伺服器", log_queue)
    logger.info("準備啟動 API 伺服器...")

    from src import main
    main.log_queue = log_queue
    main.task_queue = task_queue
    main.result_queue = result_queue

    logger.info(f"API 伺服器即將在 http://{config.WEBSOCKET_HOST}:{config.WEBSOCKET_PORT} 上運行")
    try:
        uvicorn.run(
            app,
            host=config.WEBSOCKET_HOST,
            port=config.WEBSOCKET_PORT,
            log_config=None,
            log_level="debug"
        )
    except Exception as e:
        logger.error(f"Uvicorn 運行時發生錯誤: {e}")
    logger.info("API 伺服器已關閉。")


def launcher_main(profile: str, num_workers: int):
    """
    這是從 src/launcher.py 移植過來的主函式，負責啟動並管理所有子行程。
    """
    log_queue = mp.Queue()
    logger = get_logger("智慧啟動器", log_queue)

    try:
        config = get_config(profile)
        logger.info("--- 鳳凰錄音轉寫服務 ---")
        logger.info(f"成功載入配置: {config.PROFILE_NAME}")
    except ValueError as e:
        logger.error(f"設定檔錯誤: {e}")
        return

    logger.info("核心作戰準則：擁抱韌性設計、建立可觀測性。")

    processes = []
    try:
        task_queue = mp.Queue()
        result_queue = mp.Queue()
        logger.info("已成功建立任務佇列、結果佇列與日誌佇列。")

        log_writer = mp.Process(target=log_writer_process, args=(log_queue,), name="LogWriterProcess")
        processes.append(log_writer)

        api_process = mp.Process(
            target=start_api_server,
            args=(log_queue, task_queue, result_queue, config),
            name="APIServerProcess"
        )
        processes.append(api_process)

        if profile == "testing":
            logger.info("偵測到 'testing' 環境，將啟動模擬工人。")
            worker_target = mock_worker_process
            worker_name = "MockWorkerProcess"
        else:
            logger.info("將啟動真實的轉錄工人。")
            worker_target = transcriber_worker_process
            worker_name = "IntelligentWorkerProcess"

        for i in range(num_workers):
            worker_process_instance = mp.Process(
                target=worker_target,
                args=(log_queue, task_queue, result_queue, config),
                name=f"{worker_name}-{i+1}"
            )
            processes.append(worker_process_instance)

        for p in processes:
            p.daemon = True
            logger.info(f"正在啟動 {p.name} 行程...")
            p.start()

        logger.info("所有核心服務已啟動。主行程將保持運行以監控子行程。")
        logger.info("按 Ctrl+C 以終止所有服務。")

        while True:
            time.sleep(1)
            for p in processes:
                if not p.is_alive():
                    logger.warning(f"行程 {p.name} (PID: {p.pid}) 已意外終止！")
                    logger.warning(f"行程 {p.name} 的 exitcode 是: {p.exitcode}")
                    raise RuntimeError(f"{p.name} 已終止")

    except (KeyboardInterrupt, RuntimeError) as e:
        if isinstance(e, KeyboardInterrupt):
            logger.info("收到使用者中斷信號 (Ctrl+C)。")
        else:
            logger.error(f"偵測到嚴重錯誤，將關閉所有服務: {e}")

    finally:
        logger.info("開始執行關閉程序...")
        if 'worker_process_instance' in locals() and worker_process_instance.is_alive():
            try:
                logger.info("正在發送關閉信號至工人行程...")
                task_queue.put(None, timeout=1)
            except Exception as e:
                logger.warning(f"發送關閉信號至工人失敗: {e}，可能將強制終止。")

        for p in reversed(processes):
            if p.name == "LogWriterProcess": continue
            if p.is_alive():
                logger.info(f"正在終止 {p.name}...")
                p.terminate()

        for p in reversed(processes):
            if p.name == "LogWriterProcess": continue
            p.join(timeout=5)

        if 'log_writer' in locals() and log_writer.is_alive():
            logger.info("正在關閉日誌書記官行程...")
            log_queue.put(None)
            log_writer.join(timeout=2)

        logger.info("所有服務已關閉。再會。")


@cli.command(name="run-server")
@click.option(
    "--profile",
    type=click.Choice(["testing", "production"], case_sensitive=False),
    default="testing",
    help="選擇要使用的作戰配置 (預設: testing)"
)
@click.option(
    "--num-workers",
    type=int,
    default=1,
    help="要啟動的轉寫工人數量 (預設: 1)"
)
def run_server(profile, num_workers):
    """
    啟動 API 伺服器以及對應的背景工人行程。
    """
    click.echo(f"==> 準備以 '{profile}' 配置啟動服務...")
    click.echo(f"==> 將啟動 {num_workers} 個轉寫工人...")
    # 設定 multiprocessing 啟動方法
    # 在某些系統上，需要 force=True
    if sys.platform == "darwin":
         mp.set_start_method("spawn", force=True)
    else:
         mp.set_start_method("spawn")

    launcher_main(profile, num_workers)


@cli.command(name="install-deps")
def install_deps():
    """
    使用 uv 安裝或更新專案所需的所有 Python 依賴套件。
    如果 uv 不存在，會先自動安裝。
    """
    # --- 步驟 1: 檢查 uv 是否存在 ---
    try:
        subprocess.check_call([sys.executable, "-m", "uv", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        click.echo("==> uv 已安裝。")
    except (subprocess.CalledProcessError, FileNotFoundError):
        click.echo("==> 'uv' 未找到，正在自動安裝...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "uv"])
            click.secho("==> uv 安裝成功。", fg="green")
        except subprocess.CalledProcessError as e:
            click.secho(f"==> uv 安裝失敗: {e}", fg="red")
            sys.exit(1)

    # --- 步驟 2: 使用 uv 安裝依賴 ---
    click.echo("==> 正在使用 uv 安裝/更新依賴套件 (來自 pyproject.toml)...")
    try:
        subprocess.check_call([sys.executable, "-m", "uv", "pip", "install", "-p", sys.executable, "."])
        click.secho("==> 依賴套件安裝成功。", fg="green")
    except subprocess.CalledProcessError as e:
        click.secho(f"==> 依賴套件安裝失敗: {e}", fg="red")
        sys.exit(1)


@cli.command(name="run-tests")
def run_tests():
    """
    執行完整的自動化測試套件，並自動設定正確的 PYTHONPATH。
    """
    click.echo("==> 正在設定測試環境...")
    test_env = os.environ.copy()
    # 關鍵修正：將專案根目錄加入 PYTHONPATH，讓測試能找到模組
    project_root = os.path.abspath(os.path.dirname(__file__))
    current_pythonpath = test_env.get("PYTHONPATH", "")
    test_env["PYTHONPATH"] = f".:{current_pythonpath}"

    click.echo(f"==> PYTHONPATH 已設定為: {test_env['PYTHONPATH']}")
    click.echo("==> 正在啟動 pytest...")
    try:
        # 使用修改後的環境變數來執行測試
        subprocess.check_call([sys.executable, "-m", "pytest", "-v"], env=test_env)
        click.secho("==> 所有測試皆已通過。", fg="green")
    except subprocess.CalledProcessError as e:
        click.secho(f"==> 測試失敗: {e}", fg="red")
        sys.exit(1)
    except FileNotFoundError:
        click.secho("==> 錯誤: 'pytest' 未找到。請先執行 'install-deps'。", fg="red")
        sys.exit(1)


if __name__ == "__main__":
    cli()
