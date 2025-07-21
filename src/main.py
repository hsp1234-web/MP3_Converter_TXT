"""
主應用程式檔案 - Uvicorn 指揮官模式
"""
import logging
import multiprocessing as mp
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

import aiofiles
import aiosqlite
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.core import DATABASE_FILE, UPLOAD_DIR
from src.core.log_config import log_listener_process, setup_worker_logging
from src.mock_worker import mock_worker_process

# --- 全局日誌記錄器 ---
# 在 lifespan 啟動日誌監聽器之前，日誌會進入控制台
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FastAPI_App")

# --- 常數 ---
NUM_WORKERS = 2  # 定義要啟動的工人數量

# --- Pre-emptive directory creation ---
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
Path("logs").mkdir(exist_ok=True) # 為日誌檔案建立目錄


# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    處理應用程式啟動和關閉事件的生命週期管理器。
    這是整個多進程架構的指揮中心。
    """
    logger.info("【指揮中心】: 應用程式啟動程序開始...")

    # --- 1. 建立進程管理器和共享佇列 ---
    manager = mp.Manager()
    app.state.task_queue = manager.Queue()
    app.state.log_queue = manager.Queue()
    logger.info("【指揮中心】: 已成功建立進程共享的任務佇列和日誌佇列。")

    # --- 2. 啟動日誌監聽器進程 ---
    log_listener = mp.Process(
        target=log_listener_process,
        args=(app.state.log_queue,),
        name="LogListener"
    )
    log_listener.start()
    app.state.log_listener = log_listener
    # 從現在開始，所有發送到 log_queue 的日誌都將由 LogListener 處理
    setup_worker_logging(app.state.log_queue)
    logger.info("【指揮中心】: 日誌監聽器已啟動。日誌系統全面運作。")

    # --- 3. 啟動背景工人進程 ---
    app.state.workers = []
    for i in range(NUM_WORKERS):
        worker_process = mp.Process(
            target=mock_worker_process,
            args=(app.state.task_queue, app.state.log_queue),
            name=f"MockWorker-{i+1}"
        )
        worker_process.start()
        app.state.workers.append(worker_process)
        logger.info(f"【指揮中心】: 已啟動背景工人進程: {worker_process.name}")

    logger.info("【指揮中心】: 所有背景服務已啟動。Uvicorn 伺服器準備就緒。")

    yield  # 應用程式在此處運行

    # --- 應用程式關閉程序 ---
    logger.info("【指揮中心】: 應用程式關閉程序開始...")

    # --- 1. 終止背景工人 ---
    logger.info(f"【指揮中心】: 正在向 {len(app.state.workers)} 個工人發送終止信號...")
    for _ in app.state.workers:
        app.state.task_queue.put(None)  # 發送停止信號

    for worker in app.state.workers:
        worker.join(timeout=5)
        if worker.is_alive():
            logger.warning(f"【指揮中心】: 工人 {worker.name} 未能及時終止，將被強制終結。")
            worker.terminate()
    logger.info("【指揮中心】: 所有背景工人已成功關閉。")

    # --- 2. 終止日誌監聽器 ---
    logger.info("【指揮中心】: 正在關閉日誌監聽器...")
    app.state.log_queue.put(None)
    app.state.log_listener.join(timeout=5)
    if app.state.log_listener.is_alive():
        logger.warning("【指揮中心】: 日誌監聽器未能及時終止，將被強制終結。")
        app.state.log_listener.terminate()
    logger.info("【指揮中心】: 日誌系統已關閉。")
    logger.info("【指揮中心】: 應用程式已完全關閉。再會。")


# --- FastAPI App Instance ---
app = FastAPI(lifespan=lifespan)

# --- API Endpoints ---
@app.get("/health", status_code=200)
async def health_check(request: Request) -> dict[str, Any]:
    """
    深度健康檢查端點。
    檢查資料庫連接和任務佇列的健康狀況。
    """
    db_status = "ok"
    db_error = None
    queue_status = "ok"
    queue_size = -1

    # 1. 檢查資料庫連接
    try:
        async with aiosqlite.connect(DATABASE_FILE, timeout=5) as db:
            await db.execute("PRAGMA quick_check;")
    except Exception as e:
        db_status = "error"
        db_error = str(e)
        logger.error("健康檢查：資料庫連接失敗: %s", e)

    # 2. 檢查任務佇列
    try:
        if hasattr(request.app.state, 'task_queue'):
            queue_size = request.app.state.task_queue.qsize()
        else:
            queue_status = "unavailable"
    except Exception as e:
        queue_status = "error"
        logger.error("健康檢查：無法獲取任務佇列狀態: %s", e)

    response_payload = {
        "status": "ok" if db_status == "ok" and queue_status == "ok" else "error",
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "dependencies": {
            "database": {"status": db_status, "error": db_error},
            "task_queue": {"status": queue_status, "queue_size": queue_size}
        }
    }
    status_code = 200 if response_payload["status"] == "ok" else 503
    return JSONResponse(content=response_payload, status_code=status_code)


@app.post("/upload", status_code=202)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
) -> dict[str, str]:
    """接受檔案上傳，儲存檔案，並在共享佇列中建立一個新的轉錄任務。"""
    task_id = str(uuid.uuid4())
    filepath = UPLOAD_DIR / f"{task_id}_{file.filename}"
    task_queue = request.app.state.task_queue

    try:
        async with aiofiles.open(filepath, "wb") as out_file:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                await out_file.write(content)
        logger.info("檔案 '%s' 已上傳至 '%s'", file.filename, filepath)

        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute(
                "INSERT INTO transcription_tasks (id, original_filepath) VALUES (?, ?)",
                (task_id, str(filepath)),
            )
            await db.commit()
        logger.info("任務 %s 的元數據已存入資料庫。", task_id)

        task_queue.put(task_id)
        logger.info("任務 %s 已成功放入任務佇列。", task_id)

    except IOError as e:
        logger.exception("檔案操作失敗: %s", e)
        raise HTTPException(status_code=500, detail="檔案操作失敗。") from e
    except Exception as e:
        logger.exception("後端處理上傳時發生未知錯誤: %s", e)
        raise HTTPException(status_code=500, detail="伺服器內部錯誤。") from e

    return {"task_id": task_id}


@app.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
) -> dict[str, Any]:
    """查詢並返回任務的狀態和結果。"""
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM transcription_tasks WHERE id = ?", (task_id,)
            ) as cursor:
                task = await cursor.fetchone()

        if task is None:
            raise HTTPException(status_code=404, detail="找不到任務 ID")

        return dict(task)

    except aiosqlite.Error as e:
        logger.exception("查詢任務 %s 狀態時出錯: %s", task_id, e)
        raise HTTPException(status_code=500, detail="查詢狀態時出錯。") from e


# --- Mount Static Files ---
# 確保這在所有 API 路由之後
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
