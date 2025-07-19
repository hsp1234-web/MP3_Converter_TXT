import uuid
import aiofiles
from pathlib import Path
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from src.logger import get_logger
from src.database import initialize_database, DATABASE_FILE, UPLOAD_DIR

# --- Pre-emptive directory creation ---
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

# --- Constants & Settings ---
logger = get_logger(__name__)

# --- Database Dependency ---
def get_db():
    """
    FastAPI dependency to get a database connection.
    It also ensures the database is initialized before the first connection.
    `check_same_thread=False` is required for SQLite with FastAPI as FastAPI
    can use multiple threads to interact with the dependency.
    """
    initialize_database() # Ensure table exists on every startup
    db = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    try:
        yield db
    finally:
        db.close()

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI application startup...")
    # Initialization is now handled by the get_db dependency
    yield
    logger.info("FastAPI application shutdown...")

# --- FastAPI App Instance ---
app = FastAPI(lifespan=lifespan)

# --- API Endpoints ---
@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

@app.post("/upload", status_code=202)
async def upload_file(file: UploadFile = File(...), db: sqlite3.Connection = Depends(get_db)):
    """
    Accepts a file upload, saves it, and creates a new transcription task in the database.
    """
    task_id = str(uuid.uuid4())
    filepath = UPLOAD_DIR / f"{task_id}_{file.filename}"

    try:
        async with aiofiles.open(filepath, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        logger.info(f"File '{file.filename}' uploaded to '{filepath}'")

        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO transcription_tasks (id, original_filepath, status) VALUES (?, ?, ?)",
            (task_id, str(filepath), 'pending')
        )
        db.commit()
        logger.info(f"Task created in database with ID: {task_id}")

        return {"task_id": task_id}

    except Exception as e:
        logger.error(f"File upload or database operation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

@app.get("/status/{task_id}")
async def get_task_status(task_id: str, db: sqlite3.Connection = Depends(get_db)):
    """
    Queries and returns the status and result of a task based on its ID.
    """
    try:
        db.row_factory = sqlite3.Row
        cursor = db.cursor()

        cursor.execute("SELECT * FROM transcription_tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()

        if task is None:
            raise HTTPException(status_code=404, detail="Task ID not found")

        return dict(task)

    except Exception as e:
        logger.error(f"Error querying task status for ID {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error querying status: {e}")

# --- Mount Static Files ---
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
