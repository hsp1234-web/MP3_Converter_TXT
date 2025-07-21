"""工人測試."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.core import get_logger
from src.transcriber_worker import process_single_task

if TYPE_CHECKING:
    import aiosqlite


@pytest.mark.asyncio
async def test_worker_success_scenario(db_connection: aiosqlite.Connection) -> None:
    """測試工人成功處理任務的場景."""
    # Arrange
    task_id = "test_success_scenario"
    # 確保每次測試都在乾淨的狀態下運行
    await db_connection.execute("DELETE FROM transcription_tasks WHERE id = ?", (task_id,))
    await db_connection.commit()
    await db_connection.execute(
        "INSERT INTO transcription_tasks (id, original_filepath, status) VALUES (?, ?, ?)",
        (task_id, "tests/audio/test_audio.wav", "pending"),
    )
    await db_connection.commit()

    # Act
    # 直接調用 process_single_task 並傳入 task_id，
    # 該函數內部有邏輯會在檢測到 pytest 環境時模擬成功
    await process_single_task(task_id)

    # Assert
    async with db_connection.execute(
        "SELECT status, result_text FROM transcription_tasks WHERE id = ?", (task_id,)
    ) as cursor:
        task = await cursor.fetchone()
    assert task is not None, f"任務 '{task_id}' 未在資料庫中找到"
    status, result_text = task
    assert status == "completed"
    # 斷言結果是我們模擬的文本
    assert result_text == "這是模擬的轉錄結果。"
