"""主應用程式檔案."""
import logging
import sqlite3
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Iterator

import aiofiles
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from src.core import DATABASE_FILE, UPLOAD_DIR, get_logger, initialize_database

# --- Pre-emptive directory creation ---
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

# --- Constants & Settings ---
logger = get_logger(__name__)


# --- Database Dependency ---
def get_db() -> Iterator[sqlite3.Connection]:
    """
    FastAPI dependency to get a database connection.

    It also ensures the database is initialized before the first connection.
    `check_same_thread=False` is required for SQLite with FastAPI as FastAPI
    can use multiple threads to interact with the dependency.
    """
    initialize_database()  # Ensure table exists on every startup
    db = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    try:
        yield db
    finally:
        db.close()


# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    logger.info("FastAPI application startup...")
    # Initialization is now handled by the get_db dependency
    yield
    logger.info("FastAPI application shutdown...")


# --- FastAPI App Instance ---
app = FastAPI(lifespan=lifespan)


# --- API Endpoints ---
@app.get("/health", status_code=200)
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/upload", status_code=202)
async def upload_file(
    file: UploadFile = File(...),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, str]:
    """Accept a file upload, save it, and create a new transcription task."""
    task_id = str(uuid.uuid4())
    filepath = UPLOAD_DIR / f"{task_id}_{file.filename}"

    try:
        async with aiofiles.open(filepath, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
        logger.info("File '%s' uploaded to '%s'", file.filename, filepath)

        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO transcription_tasks (id, original_filepath, status) VALUES (?, ?, ?)",
            (task_id, str(filepath), "pending"),
        )
        db.commit()
        logger.info("Task created in database with ID: %s", task_id)

    except IOError as e:
        logger.exception("File operation failed: %s", e)
        raise HTTPException(status_code=500, detail="File operation failed.") from e
    except sqlite3.Error as e:
        logger.exception("Database operation failed: %s", e)
        raise HTTPException(status_code=500, detail="Database operation failed.") from e

    return {"task_id": task_id}


@app.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    """Query and return the status and result of a task based on its ID."""
    try:
        db.row_factory = sqlite3.Row
        cursor = db.cursor()

        cursor.execute("SELECT * FROM transcription_tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()

        if task is None:
            raise HTTPException(status_code=404, detail="Task ID not found")

        return dict(task)

    except sqlite3.Error as e:
        logger.exception("Error querying task status for ID %s: %s", task_id, e)
        raise HTTPException(status_code=500, detail="Error querying status.") from e


# --- Mount Static Files ---
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    # 當直接執行此檔案時，設定一個備用的日誌系統
    if not logger.handlers or isinstance(logger.handlers[0], logging.StreamHandler):
        # 移除預設的 StreamHandler
        if logger.hasHandlers():
            logger.handlers.clear()

        # 設定一個基本的檔案日誌
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filename="main_direct_run.log",
            filemode="w",
        )
        logger.info("以直接執行模式啟動, 使用 main_direct_run.log 進行日誌記錄.")

    uvicorn.run(app, host="127.0.0.1", port=8000)
