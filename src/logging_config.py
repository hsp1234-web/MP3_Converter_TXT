# src/logging_config.py
import logging
import logging.handlers
import multiprocessing as mp
from typing import Optional

LOG_FILENAME = "phoenix_transcriber.log"
LOG_FORMAT = '%(asctime)s - %(processName)s - %(name)s - %(levelname)s - %(message)s'

def log_writer_process(log_queue: mp.Queue):
    """
    日誌書記官行程。
    """
    file_handler = logging.FileHandler(LOG_FILENAME, encoding='utf-8')
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)

    while True:
        try:
            record = log_queue.get()
            if record is None:
                break
            logger = logging.getLogger(record.name)
            logger.handle(record)
        except Exception:
            import sys
            import traceback
            print("--- 嚴重錯誤：日誌書記官行程發生異常 ---", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

def get_logger(name: str, log_queue: Optional[mp.Queue] = None) -> logging.Logger:
    """
    獲取一個配置好的日誌記錄器實例。
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        if log_queue:
            queue_handler = logging.handlers.QueueHandler(log_queue)
            logger.addHandler(queue_handler)
        else:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(stream_handler)
            logger.warning("未提供日誌佇列，日誌將輸出到控制台。")

    return logger

def get_null_logger() -> logging.Logger:
    """
    獲取一個「空」日誌記錄器。
    """
    logger = logging.getLogger("null")
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger
