import time
import uvicorn
import logging
import multiprocessing as mp
from src.main import app
from src.mock_worker import worker_process

# --- 日誌設定 ---
# 為啟動器設定專屬的日誌格式
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger("智慧啟動器")

# --- 函式定義 ---
def start_api_server(task_queue: mp.Queue, result_queue: mp.Queue):
    """
    啟動 FastAPI (Uvicorn) 伺服器。
    此函式將在一個獨立的行程中執行。
    """
    logger.info("準備啟動 API 伺服器...")
    # 在行程啟動後，將佇列傳遞給 FastAPI 應用實例
    # 這是實現跨行程通訊的關鍵步驟
    from src import main
    main.task_queue = task_queue
    main.result_queue = result_queue

    logger.info("API 伺服器即將在 http://127.0.0.1:8000 上運行")
    # uvicorn.run() 是一個阻塞操作，它會在此處持續運行
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    logger.info("API 伺服器已關閉。")


def main():
    """
    主函式，負責建立佇列、啟動並管理所有子行程。
    """
    logger.info("--- 鳳凰錄音轉寫服務 ---")
    logger.info("核心作戰準則：擁抱韌性設計、建立可觀測性。")

    try:
        # --- 建立跨行程通訊佇列 ---
        # 必須使用 multiprocessing.Queue 而非 queue.Queue
        task_queue = mp.Queue()
        result_queue = mp.Queue()
        logger.info("已成功建立任務佇列與結果佇列。")

        # --- 建立並啟動子行程 ---
        # 1. API 伺服器行程
        api_process = mp.Process(
            target=start_api_server,
            args=(task_queue, result_queue),
            name="APIServerProcess" # 給行程一個有意義的名字
        )

        # 2. 模擬工人行程
        worker_process_instance = mp.Process(
            target=worker_process,
            args=(task_queue, result_queue),
            name="MockWorkerProcess"
        )

        # 將行程設定為守護行程 (daemon)
        # 這意味著當主行程結束時，這些子行程會被自動終止
        # 這簡化了關閉流程，但也意味著它們可能在工作中被粗暴中斷
        api_process.daemon = True
        worker_process_instance.daemon = True

        logger.info("正在啟動 API 伺服器行程...")
        api_process.start()

        logger.info("正在啟動模擬工人行程...")
        worker_process_instance.start()

        logger.info("所有核心服務已啟動。主行程將保持運行以監控子行程。")
        logger.info("按 Ctrl+C 以終止所有服務。")

        # --- 主行程迴圈 ---
        # 主行程需要保持運行，否則守護行程會立即退出
        # 我們可以透過監控子行程的存活狀態來實現優雅的關閉
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
        # 雖然守護行程會自動終止，但明確的 terminate/join 是更好的實踐
        # 這裡我們依賴守護特性進行簡化
        if 'api_process' in locals() and api_process.is_alive():
            api_process.terminate() # 強制終止
            api_process.join(timeout=5) # 等待行程結束
            logger.info("API 伺服器行程已終止。")

        if 'worker_process_instance' in locals() and worker_process_instance.is_alive():
            # 對於工人，可以先發送一個 "毒丸" 來嘗試優雅關閉
            try:
                task_queue.put(None, timeout=1)
            except Exception:
                pass # 忽略佇列已滿或已關閉的錯誤
            worker_process_instance.terminate()
            worker_process_instance.join(timeout=5)
            logger.info("模擬工人行程已終止。")

        logger.info("所有服務已關閉。再會。")


if __name__ == "__main__":
    # 設定 multiprocessing 的啟動方法為 'fork' (對 Linux/macOS 友好)
    # 或 'spawn' (對 Windows/macOS 友好且更安全)
    # 'spawn' 是更推薦的跨平台選擇，它會建立一個全新的 Python 直譯器行程
    mp.set_start_method("spawn", force=True)
    main()
