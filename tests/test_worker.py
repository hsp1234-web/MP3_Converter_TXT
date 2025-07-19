import pytest
import sqlite3
from src.transcriber_worker import process_single_task

def test_worker_success_scenario(db_connection):
    # Arrange
    cursor = db_connection.cursor()
    cursor.execute(
        "INSERT INTO transcription_tasks (id, original_filepath, status) VALUES (?, ?, ?)",
        ("test_success", "tests/audio/test_audio.wav", 'pending')
    )
    db_connection.commit()

    # Act
    process_single_task(db_connection)

    # Assert
    cursor.execute("SELECT status, result_text FROM transcription_tasks WHERE id = 'test_success'")
    task = cursor.fetchone()
    status, result_text = task
    assert status == "completed"
    assert result_text == ""

def test_worker_failure_scenario(db_connection):
    # Arrange
    cursor = db_connection.cursor()
    cursor.execute(
        "INSERT INTO transcription_tasks (id, original_filepath, status) VALUES (?, ?, ?)",
        ("test_failure", "non_existent_file.mp3", 'pending')
    )
    db_connection.commit()

    # Act
    process_single_task(db_connection)

    # Assert
    cursor.execute("SELECT status, error_message FROM transcription_tasks WHERE id = 'test_failure'")
    task = cursor.fetchone()
    status, error_message = task
    assert status == "failed"
    assert "No such file or directory" in error_message
