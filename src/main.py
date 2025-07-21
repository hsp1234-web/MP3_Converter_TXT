"""主應用程式檔案."""
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

import aiofiles
import aiosqlite
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.core import DATABASE_FILE, UPLOAD_DIR
from src.queues import add_task_to_queue

# --- Pre-emptive directory creation ---
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

import logging

# --- Constants & Settings ---
logger = logging.getLogger(__name__)


# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    logger.info("FastAPI application startup...")
    # The database initialization is now part of the server's responsibility
    # await initialize_database()
    yield
    logger.info("FastAPI application shutdown...")


# --- FastAPI App Instance ---
app = FastAPI(lifespan=lifespan)

# --- State Initialization for Standalone Debugging ---
# In a production environment, these queues are provided by the main launcher.
# For independent debugging (e.g., running with `start_api_only.sh`),
# we initialize them here to prevent AttributeError.
import multiprocessing as mp
if not hasattr(app.state, 'task_queue'):
    app.state.task_queue = mp.Queue()
if not hasattr(app.state, 'result_queue'):
    app.state.result_queue = mp.Queue()


# --- API Endpoints ---
@app.get("/health", status_code=200)
async def health_check() -> dict[str, Any]:
    """
    深度健康檢查端點。

    此端點不僅確認服務正在運行，還會檢查其核心依賴項的狀態，
    包括資料庫連接和任務佇列的健康狀況。
    """
    db_status = "ok"
    db_error = None
    queue_status = "ok"
    queue_size = -1

    # 1. 檢查資料庫連接
    try:
        async with aiosqlite.connect(DATABASE_FILE, timeout=5) as db:
            # 執行一個簡單的、不消耗資源的查詢
            await db.execute("PRAGMA quick_check;")
    except Exception as e:
        db_status = "error"
        db_error = str(e)
        logger.error("健康檢查：資料庫連接失敗: %s", e)

    # 2. 檢查任務佇列
    try:
        # 假設 task_queue 是 multiprocessing.Queue
        # 注意：qsize() 可能不是 100% 精確，但在健康檢查中足夠了
        if hasattr(app.state, 'task_queue'):
            queue_size = app.state.task_queue.qsize()
        else:
            queue_status = "unavailable"
    except Exception as e:
        queue_status = "error"
        logger.error("健康檢查：無法獲取任務佇列狀態: %s", e)


    # 3. 構建並返回響應
    response_payload = {
        "status": "ok" if db_status == "ok" and queue_status == "ok" else "error",
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "dependencies": {
            "database": {
                "status": db_status,
                "error": db_error
            },
            "task_queue": {
                "status": queue_status,
                "queue_size": queue_size
            }
        }
    }

    status_code = 200 if response_payload["status"] == "ok" else 503
    return JSONResponse(content=response_payload, status_code=status_code)


@app.post("/upload", status_code=202)
async def upload_file(
    file: UploadFile = File(...),
) -> dict[str, str]:
    """Accept a file upload, save it, and create a new transcription task."""
    task_id = str(uuid.uuid4())
    filepath = UPLOAD_DIR / f"{task_id}_{file.filename}"

    try:
        async with aiofiles.open(filepath, "wb") as out_file:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                await out_file.write(content)
        logger.info("File '%s' uploaded to '%s'", file.filename, filepath)

        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute(
                "INSERT INTO transcription_tasks (id, original_filepath) VALUES (?, ?)",
                (task_id, str(filepath)),
            )
            await db.commit()

        await add_task_to_queue(task_id)
        logger.info("Task created in database with ID: %s", task_id)

    except IOError as e:
        logger.exception("File operation failed: %s", e)
        raise HTTPException(status_code=500, detail="File operation failed.") from e
    except aiosqlite.Error as e:
        logger.exception("Database operation failed: %s", e)
        raise HTTPException(status_code=500, detail="Database operation failed.") from e

    return {"task_id": task_id}


@app.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
) -> dict[str, Any]:
    """Query and return the status and result of a task based on its ID."""
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM transcription_tasks WHERE id = ?", (task_id,)
            ) as cursor:
                task = await cursor.fetchone()

        if task is None:
            raise HTTPException(status_code=404, detail="Task ID not found")

        return dict(task)

    except aiosqlite.Error as e:
        logger.exception("Error querying task status for ID %s: %s", task_id, e)
        raise HTTPException(status_code=500, detail="Error querying status.") from e


# --- Mount Static Files ---
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
