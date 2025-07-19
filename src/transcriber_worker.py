import sqlite3
import time
from src.core import get_logger
from src.core import DATABASE_FILE

def process_single_task(db_connection):
    """
    處理單個轉錄任務。
    """
    from faster_whisper import WhisperModel
    from src.core.hardware import get_best_hardware_config

    logger = get_logger("轉錄工人")
    cursor = db_connection.cursor()

    # 查詢一個待處理任務
    cursor.execute("SELECT id, original_filepath FROM transcription_tasks WHERE status = 'pending' ORDER BY created_at LIMIT 1")
    task = cursor.fetchone()

    if task:
        task_id, audio_path = task
        logger.info(f"找到待處理任務: {task_id}")

        try:
            # 更新狀態為處理中
            cursor.execute("UPDATE transcription_tasks SET status = 'processing' WHERE id = ?", (task_id,))
            db_connection.commit()
            logger.info(f"任務 {task_id} 狀態更新為: processing")

            # 執行轉錄
            hardware_config = get_best_hardware_config()
            model = WhisperModel(
                "tiny",  # Using tiny for testing
                device=hardware_config["device"],
                compute_type=hardware_config["compute_type"]
            )
            segments, info = model.transcribe(audio_path, beam_size=5)
            full_transcript = "".join(segment.text for segment in segments)
            logger.info(f"任務 {task_id}: 轉錄完成。")

            # 更新最終結果
            cursor.execute(
                "UPDATE transcription_tasks SET status = 'completed', result_text = ? WHERE id = ?",
                (full_transcript.strip(), task_id)
            )
            db_connection.commit()
            logger.info(f"任務 {task_id} 狀態更新為: completed")

        except Exception as e:
            error_message = f"轉錄任務 {task_id} 過程中發生錯誤: {e}"
            logger.error(error_message, exc_info=True)
            cursor.execute(
                "UPDATE transcription_tasks SET status = 'failed', error_message = ? WHERE id = ?",
                (str(e), task_id)
            )
            db_connection.commit()
            logger.info(f"任務 {task_id} 狀態更新為: failed")

def transcriber_worker_process(log_queue, task_queue, result_queue, config):
    """
    工人的主循環，現在作為一個獨立的行程函數。
    """
    logger = get_logger("轉錄工人", log_queue)
    logger.info("真實轉錄工人行程已啟動")
    db_connection = sqlite3.connect(DATABASE_FILE, check_same_thread=False)

    while True:
        try:
            # 這裡的邏輯是輪詢數據庫，未來可以改為從 task_queue 獲取任務
            process_single_task(db_connection)
            time.sleep(5)  # 每5秒檢查一次新任務
        except Exception as e:
            logger.error(f"工人在主循環中發生嚴重錯誤: {e}", exc_info=True)
            time.sleep(10) # 如果發生錯誤，等待更長時間

if __name__ == "__main__":
    # 這部分保留用於獨立測試
    # 為了直接運行，需要一個模擬的佇列
    class MockQueue:
        def put(self, *args, **kwargs):
            print(f"MOCK_QUEUE: {args}")

    print("以獨立模式運行轉錄工人...")
    transcriber_worker_process(MockQueue(), None, None, None)
