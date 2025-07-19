import pytest
from src.transcriber_worker import process_single_task
import sqlite3

def test_worker_success_scenario(db_connection):
    # Arrange
    cursor = db_connection.cursor()
    # 確保每次測試都在乾淨的狀態下運行
    cursor.execute("DELETE FROM transcription_tasks WHERE id = 'test_success'")
    db_connection.commit()
    cursor.execute(
        "INSERT INTO transcription_tasks (id, original_filepath, status) VALUES (?, ?, ?)",
        ("test_success", "tests/audio/test_audio.wav", 'pending')
    )
    db_connection.commit()

    # Act
    # 在這個測試中，我們需要一個模擬的日誌佇列
    from src.logger import get_logger
    # 初始化一個假的日誌記錄器，這樣就不會因為沒有佇列而報錯
    get_logger("轉錄工人")
    process_single_task(db_connection)

    # Assert
    cursor.execute("SELECT status, result_text FROM transcription_tasks WHERE id = 'test_success'")
    task = cursor.fetchone()
    assert task is not None, "任務 'test_success' 未在資料庫中找到"
    status, result_text = task
    assert status == "completed"
    # 斷言結果不為空，因為它應該已經被成功轉錄
    assert result_text is not None
    assert len(result_text) > 0
    # 也可以做一個更具體的檢查，確認轉錄內容是否符合預期
    assert "birch" in result_text.lower()
