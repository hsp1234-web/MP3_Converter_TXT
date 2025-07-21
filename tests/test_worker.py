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
    # 確保每次測試都在乾淨的狀態下運行
    await db_connection.execute("DELETE FROM transcription_tasks WHERE id = 'test_success'")
    await db_connection.commit()
    await db_connection.execute(
        "INSERT INTO transcription_tasks (id, original_filepath, status) VALUES (?, ?, ?)",
        ("test_success", "tests/audio/test_audio.wav", "pending"),
    )
    await db_connection.commit()

    # Act
    # 在這個測試中, 我們需要一個模擬的日誌佇列
    # 初始化一個假的日誌記錄器, 這樣就不會因為沒有佇列而報錯
    get_logger("轉錄工人")
    await process_single_task()

    # Assert
    async with db_connection.execute(
        "SELECT status, result_text FROM transcription_tasks WHERE id = 'test_success'",
    ) as cursor:
        task = await cursor.fetchone()
    assert task is not None, "任務 'test_success' 未在資料庫中找到"
    status, result_text = task
    assert status == "completed"
    # 斷言結果不為空, 因為它應該已經被成功轉錄
    assert result_text is not None
    assert len(result_text) > 0
    # 也可以做一個更具體的檢查, 確認轉錄內容是否符合預期
    assert "birch" in result_text.lower()
