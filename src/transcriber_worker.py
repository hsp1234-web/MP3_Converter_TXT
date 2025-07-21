"""轉錄工人模組."""
import multiprocessing as mp
import sqlite3
import time
from typing import Any

from faster_whisper import WhisperModel

from src.core import DATABASE_FILE, get_logger
from src.core.hardware import get_best_hardware_config


def process_single_task(db_connection: sqlite3.Connection) -> None:
    """處理單個轉錄任務."""
    logger = get_logger("轉錄工人")
    cursor = db_connection.cursor()

    # 查詢一個待處理任務
    cursor.execute(
        "SELECT id, original_filepath FROM transcription_tasks WHERE status = 'pending' ORDER BY created_at LIMIT 1",
    )
    task = cursor.fetchone()

    if task:
        task_id, audio_path = task
        logger.info("找到待處理任務: %s", task_id)

        try:
            # 更新狀態為處理中
            cursor.execute(
                "UPDATE transcription_tasks SET status = 'processing' WHERE id = ?",
                (task_id,),
            )
            db_connection.commit()
            logger.info("任務 %s 狀態更新為: processing", task_id)

            # 執行轉錄
            hardware_config = get_best_hardware_config()
            model = WhisperModel(
                "tiny",  # Using tiny for testing
                device=hardware_config["device"],
                compute_type=hardware_config["compute_type"],
            )
            segments, _info = model.transcribe(audio_path, beam_size=5)
            full_transcript = "".join(segment.text for segment in segments)
            logger.info("任務 %s: 轉錄完成.", task_id)

            # 更新最終結果
            cursor.execute(
                "UPDATE transcription_tasks SET status = 'completed', result_text = ? WHERE id = ?",
                (full_transcript.strip(), task_id),
            )
            db_connection.commit()
            logger.info("任務 %s 狀態更新為: completed", task_id)

        except Exception:
            logger.exception("轉錄任務 %s 過程中發生錯誤", task_id)
            cursor.execute(
                "UPDATE transcription_tasks SET status = 'failed', error_message = ? WHERE id = ?",
                (f"轉錄任務 {task_id} 過程中發生錯誤", task_id),
            )
            db_connection.commit()
            logger.info("任務 %s 狀態更新為: failed", task_id)


def transcriber_worker_process(
    log_queue: mp.Queue,
    _task_queue: mp.Queue,
    _result_queue: mp.Queue,
    _config: dict[str, Any],
) -> None:
    """工人的主循環, 現在作為一個獨立的行程函數."""
    logger = get_logger("轉錄工人", log_queue)
    logger.info("真實轉錄工人行程已啟動")
    db_connection = sqlite3.connect(DATABASE_FILE, check_same_thread=False)

    while True:
        try:
            # 這裡的邏輯是輪詢數據庫, 未來可以改為從 task_queue 獲取任務
            process_single_task(db_connection)
            time.sleep(5)  # 每5秒檢查一次新任務
        except Exception:
            logger.exception("工人在主循環中發生嚴重錯誤")
            time.sleep(10)  # 如果發生錯誤, 等待更長時間


if __name__ == "__main__":
    # 這部分保留用於獨立測試
    # 為了直接運行, 需要一個模擬的佇列
    class MockQueue:
        """模擬佇列."""

        def put(self, *args: Any, **kwargs: Any) -> None:
            """模擬 put."""
            pass

    transcriber_worker_process(MockQueue(), mp.Queue(), mp.Queue(), {})
