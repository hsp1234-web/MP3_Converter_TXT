import asyncio
import logging
import multiprocessing as mp
import os
from typing import Any

# 由於此模組由主進程動態加載，我們需要確保 src 路徑在其中
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.log_config import setup_worker_logging

def mock_worker_process(
    task_queue: mp.Queue,
    log_queue: mp.Queue,
) -> None:
    """
    模擬的工人行程，它會監聽任務佇列並處理任務。
    它的日誌會被發送到共享的日誌佇列。
    """
    # --- 日誌設定 ---
    # 這是關鍵：工人進程不自行配置 handler，而是將日誌發送到 log_queue
    setup_worker_logging(log_queue)
    logger = logging.getLogger(f"MockWorker-{os.getpid()}")
    logger.info("模擬工人已啟動，隨時待命。")

    async def main_loop():
        while True:
            try:
                task_id = task_queue.get()
                if task_id is None:  # 收到停止信號
                    logger.info("收到終止信號，準備關閉。")
                    break

                logger.info(f"【任務 {task_id}】: 已接收，開始模擬處理...")
                await asyncio.sleep(2)  # 模擬 I/O 綁定或 CPU 密集型工作

                # 在此版本中，工人不直接寫入資料庫或結果佇列，
                # 僅僅記錄處理完成的日誌。
                # 未來的版本可以重新引入資料庫更新邏輯。
                logger.info(f"【任務 {task_id}】: 模擬處理完成。")

            except (KeyboardInterrupt, SystemExit):
                logger.info("偵測到中斷信號，正在退出...")
                break
            except Exception as e:
                logger.exception(f"主循環中發生未知錯誤: {e}")
                await asyncio.sleep(5) # 避免在連續失敗時消耗過多 CPU

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("工人被使用者強制中斷。")
    finally:
        logger.info("工人行程已完全關閉。")
