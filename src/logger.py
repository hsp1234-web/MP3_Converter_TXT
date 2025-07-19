# -*- coding: utf-8 -*-
"""
中央情報核心：一個專業、多行程安全的日誌系統。

此模組提供了鳳凰轉錄儀後端系統所需的結構化日誌功能。
它基於 Python 的 logging 與 multiprocessing 模組，確保來自不同作戰單位
(行程) 的日誌訊息能夠被集中、依序、且安全地寫入到單一的日誌檔案中。

作戰準則：
1.  **集中管理 (Centralized Control):** 所有日誌設定與格式化規則均在此模組中定義。
2.  **多程安全 (Process-Safe):** 使用 `multiprocessing.Queue` 作為緩衝區，
    避免多個行程同時寫入檔案導致的日誌混亂或損毀。
3.  **非阻塞寫入 (Non-Blocking):** 各個工作行程 (如 API 伺服器、轉錄工人)
    只需將日誌訊息放入佇列即可立即返回繼續執行任務，日誌的實際 I/O 操作
    由一個專門的「書記官」行程非同步處理。
"""
import logging
import logging.handlers
import multiprocessing as mp
from typing import Optional

# --- 常數定義 ---
LOG_FILENAME = "phoenix_transcriber.log"
LOG_FORMAT = '%(asctime)s - %(processName)s - %(name)s - %(levelname)s - %(message)s'

def log_writer_process(log_queue: mp.Queue):
    """
    日誌書記官行程。

    這是一個獨立的行程，其唯一職責是：
    1.  從共享的日誌佇列 (`log_queue`) 中讀取日誌記錄。
    2.  將日誌記錄寫入到指定的檔案中。

    透過這種方式，我們將日誌的 I/O 操作與主應用程式邏輯分離，
    避免了多行程寫入同一個檔案時可能發生的競爭和鎖定問題。
    """
    # 1. 設定此行程專用的日誌處理器
    # 這個 logger 才是真正將日誌寫入檔案的執行者。
    file_handler = logging.FileHandler(LOG_FILENAME, encoding='utf-8')
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)

    # 獲取根日誌記錄器並設定
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)

    # 2. 進入無限迴圈，作為一個守護行程持續運作
    while True:
        try:
            # 從佇列中獲取日誌記錄，這是一個阻塞操作
            record = log_queue.get()

            # "毒丸" 協議：收到 None 時，書記官行程結束
            if record is None:
                break

            # 使用日誌記錄器來處理這條記錄
            logger = logging.getLogger(record.name)
            logger.handle(record)

        except Exception:
            # 在日誌系統本身發生錯誤時，印出到標準錯誤流
            import sys
            import traceback
            print("--- 嚴重錯誤：日誌書記官行程發生異常 ---", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)


def get_logger(name: str, log_queue: Optional[mp.Queue] = None) -> logging.Logger:
    """
    獲取一個配置好的日誌記錄器實例。

    這個函數是給各個子行程 (Web 伺服器、轉錄工人等) 使用的。
    它會返回一個 logger，該 logger 不會直接將日誌寫入檔案，
    而是將日誌記錄放入一個共享的佇列中。

    Args:
        name (str): 日誌記錄器的名稱，通常是模組名 `__name__`。
        log_queue (mp.Queue): 由主行程創建並傳遞過來的共享日誌佇列。

    Returns:
        logging.Logger: 一個配置好的 logger 物件。
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 避免重複添加 handler
    if not logger.handlers:
        if log_queue:
            # 建立一個 QueueHandler，它會將所有通過此 logger 發出的日誌
            # 訊息 (LogRecord) 放入共享佇列中。
            queue_handler = logging.handlers.QueueHandler(log_queue)
            logger.addHandler(queue_handler)
        else:
            # 如果沒有提供佇列 (例如在單行程模式或測試中)，
            # 則退回到標準的控制台輸出，確保日誌不會丟失。
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(stream_handler)
            logger.warning("未提供日誌佇列，日誌將輸出到控制台。")

    return logger
