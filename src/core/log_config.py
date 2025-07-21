import logging
import logging.handlers
import multiprocessing as mp
import os
from logging.handlers import QueueHandler, QueueListener

LOG_FILE_PATH = "logs/phoenix_project.log"

def log_listener_process(log_queue: mp.Queue) -> None:
    """
    監聽日誌佇列，並將日誌記錄寫入檔案。
    這在一個獨立的進程中運行。
    """
    # --- 配置目標日誌記錄器 ---
    # 這個 handler 會將日誌寫入檔案，並進行輪轉
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE_PATH, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(name)s (%(processName)s:%(process)d) - %(message)s'
    )
    file_handler.setFormatter(formatter)

    # --- QueueListener ---
    # QueueListener 會從佇列中獲取日誌記錄，並將它們傳遞給指定的 handler
    listener = QueueListener(log_queue, file_handler)

    print(f"日誌監聽器已啟動，將記錄到 {LOG_FILE_PATH}")
    listener.start()

    try:
        # 監聽器會一直運行，直到從佇列中收到 None
        # 這是一種優雅的停止方式
        while True:
            # 我們需要一個方法來停止監聽器，通常是透過佇列傳遞一個哨兵值（如 None）
            # listener.start() 已經在一個背景執行緒中處理了這個邏輯
            # 我們的主循環只需要等待，直到被外部（例如 lifespan）終止
            record = log_queue.get()
            if record is None:
                print("日誌監聽器收到停止信號。")
                break
    except KeyboardInterrupt:
        pass
    finally:
        print("日誌監聽器正在關閉。")
        listener.stop()


def setup_worker_logging(log_queue: mp.Queue) -> None:
    """
    為子進程（例如 FastAPI 應用或背景工人）配置日誌記錄。
    它會移除所有現有的 handler，並用一個 QueueHandler 取代它們，
    這個 QueueHandler 會將所有日誌發送到共享的日誌佇列。
    """
    # 獲取根日誌記錄器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 移除所有可能已經存在的 handler
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    # 創建並添加 QueueHandler
    queue_handler = QueueHandler(log_queue)
    root_logger.addHandler(queue_handler)

    # 可選：向控制台發送一條訊息，確認日誌已重定向
    # 這有助於除錯，但這條訊息本身不會進入佇列
    # print(f"進程 {os.getpid()} 的日誌已重定向到佇列。")
