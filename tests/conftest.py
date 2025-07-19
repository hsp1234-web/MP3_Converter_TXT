import pytest
import sqlite3

@pytest.fixture
def db_connection():
    """
    Provides a clean, in-memory SQLite database connection for each test.
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transcription_tasks (
        id TEXT PRIMARY KEY,
        original_filepath TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        result_text TEXT,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    yield conn
    conn.close()
