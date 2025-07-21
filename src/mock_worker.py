import asyncio
import logging
import multiprocessing as mp
from typing import Any

def mock_worker_process(
    task_queue: mp.Queue,
    result_queue: mp.Queue,
    _config: dict[str, Any],
) -> None:
    """
    模擬的工人行程，其介面與真實的轉錄工人完全相同。
    """
    # 在新行程中，需要重新設定日誌
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
    logger = logging.getLogger("MockWorker")
    logger.info("模擬工人行程已啟動。")

    async def main_loop():
        while True:
            try:
                if not task_queue.empty():
                    task_id = task_queue.get()
                    if task_id is None: # 停止信號
                        logger.info("收到停止信號，模擬工人即將關閉。")
                        break

                    logger.info(f"任務 {task_id}: 開始模擬處理...")
                    await asyncio.sleep(2) # 模擬 I/O 綁定或 CPU 密集型工作

                    result = {
                        "task_id": task_id,
                        "status": "completed",
                        "transcript": f"這是任務 {task_id} 的模擬轉錄結果。",
                    }
                    # result_queue.put(result) # 在當前架構下，結果是寫入資料庫，而非佇列
                    logger.info(f"任務 {task_id}: 模擬處理完成，結果已（模擬）寫入。")
                else:
                    await asyncio.sleep(1) # 佇列為空時，稍作等待
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception as e:
                logger.exception(f"模擬工人在主循環中發生錯誤: {e}")
                await asyncio.sleep(5)

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("模擬工人被使用者中斷。")
    finally:
        logger.info("模擬工人行程已關閉。")
