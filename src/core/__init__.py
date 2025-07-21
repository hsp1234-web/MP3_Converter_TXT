# -*- coding: utf-8 -*-
"""
鳳凰專案核心模組.

此檔案整合了專案的通用功能, 例如配置、日誌和資料庫管理.
透過將這些功能集中在此, 我們旨在簡化導入路徑並提高程式碼的內聚性.
"""
import logging
import logging.handlers
import multiprocessing as mp
import aiosqlite
import sys
import traceback
from pathlib import Path
from typing import Type


class BaseConfig:
    """基礎設定, 所有配置都應繼承自此類別."""

    # WebSocket 伺服器設定
    WEBSOCKET_HOST = "127.0.0.1"
    WEBSOCKET_PORT = 8000

    # 預設模型設定
    MODEL_SIZE = "tiny"
    BEAM_SIZE = 1
    LANGUAGE = None  # 自動偵測


class TestingConfig(BaseConfig):
    """
    測試配置 (Testing Profile).

    - 使用極小模型, 以利於快速啟動與驗證.
    - 適用於開發、除錯及自動化整合測試.
    """

    PROFILE_NAME = "測試模式 (Testing)"
    MODEL_SIZE = "tiny"
    BEAM_SIZE = 1


class ProductionConfig(BaseConfig):
    """
    生產配置 (Production Profile).

    - 使用效能與品質均衡的模型.
    - 適用於正式作戰部署.
    - 注意: 'medium' 模型需要較多資源, 請確保硬體規格足夠.
    """

    PROFILE_NAME = "生產模式 (Production)"
    MODEL_SIZE = "medium"
    BEAM_SIZE = 5


# --- 設定檔選擇邏輯 ---

# 建立一個 profile 名稱到設定類別的映射
_PROFILES: dict[str, Type[BaseConfig]] = {
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(profile_name: str = "testing") -> BaseConfig:
    """
    根據指定的 profile 名稱獲取對應的設定實例.

    Args:
        profile_name (str): 配置檔案的名稱 (例如 "testing", "production").
                            不區分大小寫.

    Returns:
        An instance of a config class (e.g., TestingConfig).

    Raises:
        ValueError: If the profile_name is not found.

    """
    profile_key = profile_name.lower()
    config_class = _PROFILES.get(profile_key)

    if not config_class:
        msg = f"未知的設定檔: '{profile_name}'. 可用選項: {list(_PROFILES.keys())}"
        raise ValueError(msg)

    return config_class()


# --- 常數 ---
DATABASE_FILE = "transcription_tasks.db"
UPLOAD_DIR = Path("uploads")
logger = logging.getLogger(__name__)


async def initialize_database() -> None:
    """初始化資料庫和上傳目錄, 如果資料表不存在, 則建立它."""
    try:
        # 建立上傳目錄
        UPLOAD_DIR.mkdir(exist_ok=True)

        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute(
                """
            CREATE TABLE IF NOT EXISTS transcription_tasks (
                id TEXT PRIMARY KEY,
                original_filepath TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
                result_text TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            await db.execute(
                """
            CREATE TRIGGER IF NOT EXISTS update_transcription_tasks_updated_at
            AFTER UPDATE ON transcription_tasks
            FOR EACH ROW
            BEGIN
                UPDATE transcription_tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
            END;
            """
            )

            await db.commit()
        logger.info("資料庫 '%s' 和目錄 '%s' 已成功初始化.", DATABASE_FILE, UPLOAD_DIR)
    except aiosqlite.Error as e:
        logger.exception("資料庫初始化失敗: %s", e)
        raise


# --- 日誌系統 ---
"""
中央情報核心: 一個專業、多行程安全的日誌系統.

此模組提供了鳳凰轉錄儀後端系統所需的結構化日誌功能.
它基於 Python 的 logging 與 multiprocessing 模組, 確保來自不同作戰單位
(行程) 的日誌訊息能夠被集中、依序、且安全地寫入到單一的日誌檔案中.

作戰準則:
1.  **集中管理 (Centralized Control):** 所有日誌設定與格式化規則均在此模組中定義.
2.  **多程安全 (Process-Safe):** 使用 `multiprocessing.Queue` 作為緩衝區,
    避免多個行程同時寫入檔案導致的日誌混亂或損毀.
3.  **非阻塞寫入 (Non-Blocking):** 各個工作行程 (如 API 伺服器、轉錄工人)
    只需將日誌訊息放入佇列即可立即返回繼續執行任務, 日誌的實際 I/O 操作
    由一個專門的「書記官」行程非同步處理.
"""

# --- 常數定義 ---
LOG_FILENAME = "phoenix_transcriber.log"
LOG_FORMAT = "%(asctime)s - %(processName)s - %(name)s - %(levelname)s - %(message)s"


def log_writer_process(log_queue: mp.Queue) -> None:
    """
    日誌書記官行程.

    這是一個獨立的行程, 其唯一職責是:
    1.  從共享的日誌佇列 (`log_queue`) 中讀取日誌記錄.
    2.  將日誌記錄寫入到指定的檔案中.

    透過這種方式, 我們將日誌的 I/O 操作與主應用程式邏輯分離,
    避免了多行程寫入同一個檔案時可能發生的競爭和鎖定問題.
    """
    # 1. 設定此行程專用的日誌處理器
    # 這個 logger 才是真正將日誌寫入檔案的執行者.
    file_handler = logging.FileHandler(LOG_FILENAME, encoding="utf-8")
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)

    # 獲取根日誌記錄器並設定
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)

    # 2. 進入無限迴圈, 作為一個守護行程持續運作
    while True:
        try:
            # 從佇列中獲取日誌記錄, 這是一個阻塞操作
            record = log_queue.get()

            # "毒丸" 協議: 收到 None 時, 書記官行程結束
            if record is None:
                break

            # 使用日誌記錄器來處理這條記錄
            logger = logging.getLogger(record.name)
            logger.handle(record)

        except (KeyboardInterrupt, SystemExit):
            break
        except Exception:
            # 在日誌系統本身發生錯誤時, 印出到標準錯誤流
            sys.stderr.write("--- 嚴重錯誤: 日誌書記官行程發生異常 ---\n")
            traceback.print_exc(file=sys.stderr)


from typing import Optional
def get_logger(name: str, log_queue: Optional[mp.Queue] = None) -> logging.Logger:
    """
    獲取一個配置好的日誌記錄器實例.

    這個函數是給各個子行程 (Web 伺服器、轉錄工人等) 使用的.
    它會返回一個 logger, 該 logger 不會直接將日誌寫入檔案,
    而是將日誌記錄放入一個共享的佇列中.

    Args:
        name (str): 日誌記錄器的名稱, 通常是模組名 `__name__`.
        log_queue (mp.Queue | None): 由主行程創建並傳遞過來的共享日誌佇列.

    Returns:
        logging.Logger: 一個配置好的 logger 物件.

    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 避免重複添加 handler
    if not logger.handlers:
        if log_queue:
            # 建立一個 QueueHandler, 它會將所有通過此 logger 發出的日誌
            # 訊息 (LogRecord) 放入共享佇列中.
            queue_handler = logging.handlers.QueueHandler(log_queue)
            logger.addHandler(queue_handler)
        else:
            # 如果沒有提供佇列 (例如在單行程模式或測試中),
            # 則退回到標準的控制台輸出, 確保日誌不會丟失.
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(stream_handler)
            logger.warning("未提供日誌佇列, 日誌將輸出到控制台.")

    return logger


def get_null_logger() -> logging.Logger:
    """
    獲取一個「空」日誌記錄器.

    這個 logger 會忽略所有發送給它的訊息, 不執行任何 I/O 操作.
    這在測試情境下非常有用, 當我們不關心特定模組的日誌輸出時,
    可以傳遞這個 logger 來避免不必要的控制台雜訊或檔案寫入.

    Returns:
        logging.Logger: 一個不執行任何操作的 logger 物件.

    """
    logger = logging.getLogger("null")
    logger.addHandler(logging.NullHandler())
    logger.propagate = False  # 確保日誌事件不會被傳播到上層 logger
    return logger
