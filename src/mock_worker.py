"""模擬工人模組."""
import logging
import multiprocessing as mp
import time
from typing import Any

from src.core import get_logger, get_null_logger


def process_task_from_queue(
    task_queue: mp.Queue,
    result_queue: mp.Queue,
    logger: logging.Logger | None = None,
) -> None:
    """
    從任務佇列中獲取並處理單一任務.

    這是 `mock_worker_process` 的核心邏輯, 被提取出來以便在單體測試中直接調用.
    """
    if logger is None:
        logger = get_null_logger()  # 在沒有提供 logger 的情況下, 使用一個空 logger

    if task_queue.empty():
        logger.info("任務佇列為空, 無需處理.")
        return

    try:
        job = task_queue.get()
        if job is None:
            logger.info("收到結束信號, 任務處理終止.")
            # 將 None 放回佇列, 以防有其他消費者需要此信號
            task_queue.put(None)
            return

        job_id = job.get("job_id")
        logger.info("收到新任務: Job ID %s", job_id)

        # 模擬處理延遲
        time.sleep(0.01)  # 進一步縮短延遲以加速測試
        result_queue.put(
            {
                "status": "processing",
                "job_id": job_id,
                "progress": 50,
                "message": "模擬處理中...",
            },
        )
        logger.info("任務 %s: 正在模擬處理.", job_id)

        time.sleep(0.01)
        result = {
            "status": "completed",
            "job_id": job_id,
            "transcript": "這是一個模擬的轉錄結果.",
            "language": "zh",
            "duration": 10.0,
        }
        result_queue.put(result)
        logger.info("任務 %s: 模擬處理完成.", job_id)

    except Exception:
        logger.exception("處理任務時發生錯誤")


def mock_worker_process(
    log_queue: mp.Queue,
    task_queue: mp.Queue,
    result_queue: mp.Queue,
    _config: dict[str, Any],
) -> None:
    """
    模擬工人行程, 用於測試.

    現在這個行程只是 `process_task_from_queue` 函數的一個循環包裝器.
    """
    logger = get_logger("模擬工人", log_queue)
    logger.info("模擬工人行程已啟動.")

    while True:
        try:
            # 檢查是否有停止信號
            if not task_queue.empty():
                job = task_queue.get()
                if job is None:
                    logger.info("收到結束信號, 模擬工人行程即將關閉.")
                    break
                # 如果不是停止信號, 把任務放回去
                task_queue.put(job)

            process_task_from_queue(task_queue, result_queue, logger)
            time.sleep(0.1)  # 避免在沒有任務時過度消耗 CPU
        except Exception:
            logger.exception("模擬工人在主循環中發生錯誤")
