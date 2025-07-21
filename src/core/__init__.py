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
日誌系統現在由 commander_console.py 在啟動時，
通過讀取 logging_config.yaml 來進行全局配置。

所有模組都應該使用標準的 `logging.getLogger(__name__)` 來獲取 logger 實例。
不再需要自定義的 get_logger 函數或 log_writer_process。
"""

def get_logger(name: str) -> logging.Logger:
    """
    獲取一個標準的日誌記錄器實例。

    日誌的配置（例如格式、級別、輸出位置）由全局配置決定。

    Args:
        name (str): 日誌記錄器的名稱, 通常是模組名 `__name__`.

    Returns:
        logging.Logger: 一個標準的 logger 物件.
    """
    return logging.getLogger(name)


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
