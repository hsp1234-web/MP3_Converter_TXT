import multiprocessing as mp
import time
from src.logger import get_logger

def mock_worker_process(log_queue: mp.Queue, task_queue: mp.Queue, result_queue: mp.Queue, config):
    """
    模擬工人行程，用於測試。
    """
    logger = get_logger("模擬工人", log_queue)
    logger.info("模擬工人行程已啟動。")

    while True:
        try:
            job = task_queue.get()
            if job is None:
                logger.info("收到結束信號，模擬工人行程即將關閉。")
                break

            job_id = job.get("job_id")
            logger.info(f"收到新任務: Job ID {job_id}")

            # 模擬處理延遲
            time.sleep(0.1) # 縮短延遲以利測試
            result_queue.put({"status": "processing", "job_id": job_id, "progress": 50, "message": "模擬處理中..."})
            logger.info(f"任務 {job_id}: 正在模擬處理。")

            time.sleep(0.1) # 縮短延遲以利測試
            result = {
                "status": "completed",
                "job_id": job_id,
                "transcript": "這是一個模擬的轉錄結果。",
                "language": "zh",
                "duration": 10.0
            }
            result_queue.put(result)
            logger.info(f"任務 {job_id}: 模擬處理完成。")

        except Exception as e:
            logger.error(f"模擬工人在主循環中發生錯誤: {e}", exc_info=True)
