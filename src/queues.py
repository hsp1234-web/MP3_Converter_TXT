# -*- coding: utf-8 -*-
"""
基於 aiosqlite 的非同步任務佇列.

這個模組提供了一個簡單、輕量級且持久化的任務佇列.
它利用 SQLite 資料庫作為後端, 確保即使在應用程式重新啟動後,
任務也不會遺失.
"""
import asyncio
from typing import Optional

import aiosqlite

from src.core import DATABASE_FILE, get_logger

logger = get_logger(__name__)


async def add_task_to_queue(task_id: str) -> None:
    """
    將一個新任務的 ID 加入到佇列中.

    Args:
        task_id (str): 要加入佇列的任務 ID.
    """
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute(
                "UPDATE transcription_tasks SET status = 'pending' WHERE id = ?",
                (task_id,),
            )
            await db.commit()
            logger.info("任務 %s 已成功加入佇列.", task_id)
    except aiosqlite.Error as e:
        logger.exception("將任務 %s 加入佇列時發生資料庫錯誤: %s", task_id, e)
        raise


async def get_task_from_queue() -> Optional[str]:
    """
    從佇列中獲取一個待處理的任務.

    此函數會尋找狀態為 'pending' 的任務, 將其狀態更新為 'processing',
    然後返回其 ID. 這是原子操作, 以避免多個工人獲取同一個任務.

    Returns:
        Optional[str]: 如果找到待處理任務, 則返回任務 ID; 否則返回 None.
    """
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            # 原子性地尋找並鎖定一個 'pending' 任務
            async with db.execute(
                "SELECT id FROM transcription_tasks WHERE status = 'pending' LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    task_id = row[0]
                    await db.execute(
                        "UPDATE transcription_tasks SET status = 'processing' WHERE id = ?",
                        (task_id,),
                    )
                    await db.commit()
                    logger.info("從佇列中領取任務 %s.", task_id)
                    return task_id
            return None
    except aiosqlite.Error as e:
        logger.exception("從佇列獲取任務時發生資料庫錯誤: %s", e)
        return None


async def update_task_status(
    task_id: str, status: str, result_text: Optional[str] = None, error_message: Optional[str] = None
) -> None:
    """
    更新任務的狀態、結果或錯誤訊息.

    Args:
        task_id (str): 要更新的任務 ID.
        status (str): 新的狀態 ('completed', 'failed', 'retry_pending').
        result_text (Optional[str]): 轉錄成功時的結果文字.
        error_message (Optional[str]): 轉錄失敗時的錯誤訊息.
    """
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute(
                """
                UPDATE transcription_tasks
                SET status = ?, result_text = ?, error_message = ?
                WHERE id = ?
                """,
                (status, result_text, error_message, task_id),
            )
            await db.commit()
            logger.info("任務 %s 的狀態已更新為 %s.", task_id, status)
    except aiosqlite.Error as e:
        logger.exception("更新任務 %s 狀態時發生資料庫錯誤: %s", task_id, e)
        raise
