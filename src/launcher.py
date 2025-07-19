import time
import uvicorn
import logging
import argparse
import multiprocessing as mp
import sys
import os

# 將專案根目錄添加到 Python 路徑中
# 這確保了無論從哪裡執行此腳本，`src` 模組都能被正確找到
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app
from src.config import get_config
from src.transcriber_worker import transcribe_worker

# --- 日誌設定 ---
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger("智慧啟動器")

# --- 函式定義 ---
def start_api_server(task_queue: mp.Queue, result_queue: mp.Queue, config):
    """
    啟動 FastAPI (Uvicorn) 伺服器。
    """
    logger.info("準備啟動 API 伺服器...")
    from src import main
    main.task_queue = task_queue
    main.result_queue = result_queue

    logger.info(f"API 伺服器即將在 http://{config.WEBSOCKET_HOST}:{config.WEBSOCKET_PORT} 上運行")
    uvicorn.run(app, host=config.WEBSOCKET_HOST, port=config.WEBSOCKET_PORT, log_level="info")
    logger.info("API 伺服器已關閉。")

def start_worker(task_queue: mp.Queue, result_queue: mp.Queue, config):
    """
    啟動轉錄工人。
    這個函數會持續從任務隊列中獲取任務並處理。
    """
    logger.info(f"轉錄工人已啟動，使用模型: {config.MODEL_SIZE}, Beam Size: {config.BEAM_SIZE}")

    while True:
        try:
            # 從隊列中獲取任務，這是一個阻塞操作
            job = task_queue.get()

            # "毒丸" 協議：收到 None 時，工人進程結束
            if job is None:
                logger.info("收到結束信號，工人進程即將關閉。")
                break

            job_id = job.get("job_id")
            audio_path = job.get("audio_path")

            logger.info(f"工人收到新任務: Job ID {job_id}, 音檔: {audio_path}")

            # 呼叫真實的轉錄工人函數
            transcribe_worker(
                queue=result_queue,
                job_id=job_id,
                audio_path=audio_path,
                model_size=config.MODEL_SIZE,
                beam_size=config.BEAM_SIZE,
                language=config.LANGUAGE
            )

        except Exception as e:
            logger.error(f"工人在處理任務時發生錯誤: {e}", exc_info=True)

def main(args):
    """
    主函式，負責建立佇列、啟動並管理所有子行程。
    """
    # --- 讀取設定 ---
    try:
        config = get_config(args.profile)
        logger.info(f"--- 鳳凰錄音轉寫服務 ---")
        logger.info(f"成功載入配置: {config.PROFILE_NAME}")
    except ValueError as e:
        logger.error(f"設定檔錯誤: {e}")
        return

    logger.info("核心作戰準則：擁抱韌性設計、建立可觀測性。")

    try:
        # --- 建立跨行程通訊佇列 ---
        task_queue = mp.Queue()
        result_queue = mp.Queue()
        logger.info("已成功建立任務佇列與結果佇列。")

        # --- 建立並啟動子行程 ---
        # 1. API 伺服器行程
        api_process = mp.Process(
            target=start_api_server,
            args=(task_queue, result_queue, config),
            name="APIServerProcess"
        )

        # 2. 智慧工人行程
        worker_process_instance = mp.Process(
            target=start_worker,
            args=(task_queue, result_queue, config),
            name="IntelligentWorkerProcess"
        )

        api_process.daemon = True
        worker_process_instance.daemon = True

        logger.info("正在啟動 API 伺服器行程...")
        api_process.start()

        logger.info("正在啟動智慧工人行程...")
        worker_process_instance.start()

        logger.info("所有核心服務已啟動。主行程將保持運行以監控子行程。")
        logger.info("按 Ctrl+C 以終止所有服務。")

        # --- 主行程迴圈 ---
        while True:
            time.sleep(1)
            if not api_process.is_alive():
                logger.warning("API 伺服器行程已意外終止！")
                break
            if not worker_process_instance.is_alive():
                logger.warning("工人行程已意外終止！")
                break

    except KeyboardInterrupt:
        logger.info("收到使用者中斷信號 (Ctrl+C)。")
    except Exception as e:
        logger.error(f"啟動器發生未預期的嚴重錯誤: {e}", exc_info=True)
    finally:
        logger.info("開始執行關閉程序...")

        if 'worker_process_instance' in locals() and worker_process_instance.is_alive():
            try:
                # 發送 "毒丸" 讓工人優雅地完成當前任務後退出
                task_queue.put(None, timeout=1)
                logger.info("已發送關閉信號至工人行程。")
            except Exception:
                logger.warning("發送關閉信號至工人失敗，可能將強制終止。")

            worker_process_instance.join(timeout=10) # 給工人一些時間來結束
            if worker_process_instance.is_alive():
                worker_process_instance.terminate()
                worker_process_instance.join(timeout=5)
            logger.info("智慧工人行程已終止。")

        if 'api_process' in locals() and api_process.is_alive():
            api_process.terminate()
            api_process.join(timeout=5)
            logger.info("API 伺服器行程已終止。")

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
