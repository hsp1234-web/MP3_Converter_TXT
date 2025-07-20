import sqlite3
import time
import uuid
from pathlib import Path
from fastapi import UploadFile
from src.config import BaseConfig
from src.database import DATABASE_FILE, UPLOAD_DIR
from src.logging_config import get_logger
from src.model_loader import load_model

def process_audio_file(file: UploadFile, model_instance):
    """
    處理上傳的音訊檔案。
    """
    logger = get_logger("transcriber_worker")
    task_id = str(uuid.uuid4())
    filepath = UPLOAD_DIR / f"{task_id}_{file.filename}"

    try:
        # 保存上傳的檔案
        with open(filepath, "wb") as buffer:
            buffer.write(file.file.read())
        logger.info(f"檔案已儲存到: {filepath}")

        # 在資料庫中建立任務
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transcription_tasks (id, original_filepath) VALUES (?, ?)",
            (task_id, str(filepath))
        )
        conn.commit()
        conn.close()
        logger.info(f"任務 {task_id} 已建立。")

    except Exception as e:
        logger.error(f"處理檔案時發生錯誤: {e}", exc_info=True)


def transcriber_worker_process(log_queue, task_queue, result_queue, config: BaseConfig):
    """
    工人的主循環，現在作為一個獨立的行程函數。
    """
    logger = get_logger("轉錄工人", log_queue)
    logger.info("真實轉錄工人行程已啟動")
    model = load_model(config)
    db_connection = sqlite3.connect(DATABASE_FILE, check_same_thread=False)

    while True:
        try:
            task_id, audio_path = task_queue.get()
            logger.info(f"收到任務: {task_id}")

            cursor = db_connection.cursor()
            try:
                # 更新狀態為處理中
                cursor.execute("UPDATE transcription_tasks SET status = 'processing' WHERE id = ?", (task_id,))
                db_connection.commit()
                logger.info(f"任務 {task_id} 狀態更新為: processing")

                # 執行轉錄
                segments, info = model.transcribe(audio_path, beam_size=config.model.beam_size, language=config.model.language)
                full_transcript = "".join(segment.text for segment in segments)
                logger.info(f"任務 {task_id}: 轉錄完成。")

                # 更新最終結果
                cursor.execute(
                    "UPDATE transcription_tasks SET status = 'completed', result_text = ? WHERE id = ?",
                    (full_transcript.strip(), task_id)
                )
                db_connection.commit()
                logger.info(f"任務 {task_id} 狀態更新為: completed")
                result_queue.put((task_id, "completed", full_transcript.strip()))

            except Exception as e:
                error_message = f"轉錄任務 {task_id} 過程中發生錯誤: {e}"
                logger.error(error_message, exc_info=True)
                cursor.execute(
                    "UPDATE transcription_tasks SET status = 'failed', error_message = ? WHERE id = ?",
                    (str(e), task_id)
                )
                db_connection.commit()
                logger.info(f"任務 {task_id} 狀態更新為: failed")
                result_queue.put((task_id, "failed", str(e)))

        except Exception as e:
            logger.error(f"工人在主循環中發生嚴重錯誤: {e}", exc_info=True)
            time.sleep(10)
