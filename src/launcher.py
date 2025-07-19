import time
import uvicorn
import argparse
import multiprocessing as mp
import sys
import os

# 將專案根目錄添加到 Python 路徑中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app
from src.config import get_config
from src.transcriber_worker import transcriber_worker_process
from src.mock_worker import mock_worker_process
from src.logger import get_logger, log_writer_process

# --- 函式定義 ---
def start_api_server(log_queue: mp.Queue, task_queue: mp.Queue, result_queue: mp.Queue, config):
    """
    啟動 FastAPI (Uvicorn) 伺服器。
    此函數在一個獨立的子行程中執行。
    """
    # 在子行程中，使用傳入的佇列來設定 logger
    logger = get_logger("API伺服器", log_queue)
    logger.info("準備啟動 API 伺服器...")

    from src import main
    # 將佇列傳遞給 FastAPI 應用模組
    main.log_queue = log_queue
    main.task_queue = task_queue
    main.result_queue = result_queue

    logger.info(f"API 伺服器即將在 http://{config.WEBSOCKET_HOST}:{config.WEBSOCKET_PORT} 上運行")
    # 設定 uvicorn 的日誌，使其也使用我們的佇列
    uvicorn.run(
        app,
        host=config.WEBSOCKET_HOST,
        port=config.WEBSOCKET_PORT,
        log_config=None # 禁用 uvicorn 預設日誌設定
    )
    logger.info("API 伺服器已關閉。")


def main(args):
    """
    主函式，負責建立佇列、啟動並管理所有子行程。
    """
    # --- 建立日誌佇列與主行程日誌記錄器 ---
    log_queue = mp.Queue()
    logger = get_logger("智慧啟動器", log_queue)

    # --- 讀取設定 ---
    try:
        config = get_config(args.profile)
        logger.info(f"--- 鳳凰錄音轉寫服務 ---")
        logger.info(f"成功載入配置: {config.PROFILE_NAME}")
    except ValueError as e:
        logger.error(f"設定檔錯誤: {e}")
        return

    logger.info("核心作戰準則：擁抱韌性設計、建立可觀測性。")

    # --- 建立子行程列表與關閉事件 ---
    processes = []
    try:
        # --- 建立跨行程通訊佇列 ---
        task_queue = mp.Queue()
        result_queue = mp.Queue()
        logger.info("已成功建立任務佇列、結果佇列與日誌佇列。")

        # --- 建立並啟動子行程 ---
        # 1. 日誌書記官行程
        log_writer = mp.Process(target=log_writer_process, args=(log_queue,), name="LogWriterProcess")
        processes.append(log_writer)

        # 2. API 伺服器行程
        api_process = mp.Process(
            target=start_api_server,
            args=(log_queue, task_queue, result_queue, config),
            name="APIServerProcess"
        )
        processes.append(api_process)

        # 3. 智慧工人行程 (根據環境選擇)
        if args.profile == "testing":
            logger.info("偵測到 'testing' 環境，將啟動模擬工人。")
            worker_target = mock_worker_process
            worker_name = "MockWorkerProcess"
        else:
            logger.info("將啟動真實的轉錄工人。")
            worker_target = transcriber_worker_process
            worker_name = "IntelligentWorkerProcess"

        worker_process_instance = mp.Process(
            target=worker_target,
            args=(log_queue, task_queue, result_queue, config),
            name=worker_name
        )
        processes.append(worker_process_instance)

        # --- 啟動所有行程 ---
        for p in processes:
            p.daemon = True
            logger.info(f"正在啟動 {p.name} 行程...")
            p.start()

        logger.info("所有核心服務已啟動。主行程將保持運行以監控子行程。")
        logger.info("按 Ctrl+C 以終止所有服務。")

        # --- 主行程迴圈 ---
        while True:
            time.sleep(1)
            for p in processes:
                if not p.is_alive():
                    logger.warning(f"行程 {p.name} (PID: {p.pid}) 已意外終止！")
                    raise RuntimeError(f"{p.name} 已終止")

    except (KeyboardInterrupt, RuntimeError) as e:
        if isinstance(e, KeyboardInterrupt):
            logger.info("收到使用者中斷信號 (Ctrl+C)。")
        else:
            logger.error(f"偵測到嚴重錯誤，將關閉所有服務: {e}")

    finally:
        logger.info("開始執行關閉程序...")

        # --- 優雅地終止工人行程 ---
        if 'worker_process_instance' in locals() and worker_process_instance.is_alive():
            try:
                logger.info("正在發送關閉信號至工人行程...")
                task_queue.put(None, timeout=1) # 發送 "毒丸"
            except Exception as e:
                logger.warning(f"發送關閉信號至工人失敗: {e}，可能將強制終止。")

        # --- 終止所有行程 ---
        for p in reversed(processes):
            if p.name == "LogWriterProcess": continue # 日誌行程最後關閉
            if p.is_alive():
                logger.info(f"正在終止 {p.name}...")
                p.terminate()

        # 等待行程結束
        for p in reversed(processes):
            if p.name == "LogWriterProcess": continue
            p.join(timeout=5)
            if p.is_alive():
                logger.warning(f"{p.name} 未能在5秒內結束，將被強制終止。")
                # p.kill() # 在 terminate 無效時的最後手段

        # --- 最後，關閉日誌書記官 ---
        if 'log_writer' in locals() and log_writer.is_alive():
            logger.info("正在關閉日誌書記官行程...")
            log_queue.put(None) # 發送 "毒丸"
            log_writer.join(timeout=2)

        logger.info("所有服務已關閉。再會。")


if __name__ == "__main__":
    # --- 命令列參數解析 ---
    parser = argparse.ArgumentParser(description="鳳凰轉錄儀 - 智慧啟動器")
    parser.add_argument(
        "--profile",
        type=str,
        default="testing",
        choices=["testing", "production"],
        help="選擇要使用的作戰配置 (預設: testing)"
    )
    args = parser.parse_args()

    # --- 設定 multiprocessing 啟動方法 ---
    mp.set_start_method("spawn", force=True)
    main(args)
