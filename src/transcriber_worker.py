"""轉錄工人模組."""
import asyncio
import multiprocessing as mp
import time
from typing import Any

from faster_whisper import WhisperModel

import aiosqlite

from src.core import DATABASE_FILE, get_logger
from src.core.hardware import get_best_hardware_config
from src.queues import get_task_from_queue, update_task_status


async def process_single_task() -> None:
    """處理單個轉錄任務."""
    logger = get_logger("轉錄工人")
    task_id = await get_task_from_queue()

    if task_id:
        logger.info("找到待處理任務: %s", task_id)

        try:
            # 執行轉錄
            hardware_config = get_best_hardware_config()
            model = WhisperModel(
                "tiny",  # Using tiny for testing
                device=hardware_config["device"],
                compute_type=hardware_config["compute_type"],
            )
            async with aiosqlite.connect(DATABASE_FILE) as db:
                async with db.execute(
                    "SELECT original_filepath FROM transcription_tasks WHERE id = ?",
                    (task_id,),
                ) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        logger.error("在資料庫中找不到任務 %s 的檔案路徑。", task_id)
                        return
                    audio_path = row[0]
            segments, _info = model.transcribe(audio_path, beam_size=5)
            full_transcript = "".join(segment.text for segment in segments)
            logger.info("任務 %s: 轉錄完成.", task_id)

            # 更新最終結果
            await update_task_status(
                task_id, "completed", result_text=full_transcript.strip()
            )
            logger.info("任務 %s 狀態更新為: completed", task_id)

        except Exception as e:
            logger.exception("轉錄任務 %s 過程中發生錯誤", task_id)
            await update_task_status(task_id, "failed", error_message=str(e))
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

    async def main() -> None:
        while True:
            try:
                await process_single_task()
                await asyncio.sleep(5)  # 每5秒檢查一次新任務
            except Exception:
                logger.exception("工人在主循環中發生嚴重錯誤")
                await asyncio.sleep(10)  # 如果發生錯誤, 等待更長時間

    asyncio.run(main())


if __name__ == "__main__":
    # 這部分保留用於獨立測試
    # 為了直接運行, 需要一個模擬的佇列
    class MockQueue:
        """模擬佇列."""

        def put(self, *args: Any, **kwargs: Any) -> None:
            """模擬 put."""
            pass

    transcriber_worker_process(MockQueue(), mp.Queue(), mp.Queue(), {})
