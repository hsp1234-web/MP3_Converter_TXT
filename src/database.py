import sqlite3
import logging
from pathlib import Path

# --- 常數 ---
DATABASE_FILE = "transcription_tasks.db"
UPLOAD_DIR = Path("uploads")
logger = logging.getLogger(__name__)

def initialize_database():
    """
    初始化資料庫和上傳目錄。如果資料表不存在，則建立它。
    """
    try:
        # 建立上傳目錄
        UPLOAD_DIR.mkdir(exist_ok=True)

        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # 建立 transcription_tasks 資料表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcription_tasks (
            id TEXT PRIMARY KEY,
            original_filepath TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
            result_text TEXT,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 建立一個觸發器，在每次更新時自動更新 updated_at 欄位
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS update_transcription_tasks_updated_at
        AFTER UPDATE ON transcription_tasks
        FOR EACH ROW
        BEGIN
            UPDATE transcription_tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        """)

        conn.commit()
        conn.close()
        logger.info(f"資料庫 '{DATABASE_FILE}' 和目錄 '{UPLOAD_DIR}' 已成功初始化。")
    except Exception as e:
        logger.error(f"資料庫初始化失敗: {e}", exc_info=True)
        raise
