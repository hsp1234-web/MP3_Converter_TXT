import asyncio
import uuid
import aiofiles
from pathlib import Path
from multiprocessing import Queue
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from src.logger import get_logger

# --- 常數與設定 ---
UPLOAD_DIR = Path("IN")
UPLOAD_DIR.mkdir(exist_ok=True)

# --- FastAPI 應用程式實例 ---
app = FastAPI()

# --- 全域變數 (由 launcher 賦值) ---
# 這些變數將在應用程式啟動時由 `launcher.py` 注入。
log_queue: Queue = None
task_queue: Queue = None
result_queue: Queue = None
logger = None # 將在 startup 事件中初始化

# --- WebSocket 管理 ---
class ConnectionManager:
    def __init__(self, logger_instance):
        self.active_connections: list[WebSocket] = []
        self.logger = logger_instance

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        if self.logger:
            self.logger.info("一個新的 WebSocket 客戶端已連線。")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if self.logger:
            self.logger.info("一個 WebSocket 客戶端已離線。")

    async def broadcast(self, message: dict):
        """向所有連線的客戶端廣播訊息"""
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"向客戶端傳送訊息失敗: {e}, 可能客戶端已非正常關閉。")

# --- 背景任務 ---
async def process_results():
    """
    一個非同步的背景任務，持續從結果佇列中讀取訊息並透過 WebSocket 廣播。
    """
    logger.info("結果處理迴圈已啟動。")
    loop = asyncio.get_running_loop()
    while True:
        if not result_queue.empty():
            try:
                result = await loop.run_in_executor(None, result_queue.get)
                logger.info(f"從結果佇列收到訊息: {result}")
                await app.state.manager.broadcast(result)
            except Exception as e:
                logger.error(f"處理結果佇列時發生錯誤: {e}", exc_info=True)
        await asyncio.sleep(0.1)

# --- FastAPI 事件處理 ---
@app.on_event("startup")
async def startup_event():
    """應用啟動時執行的事件"""
    global logger
    # 從全域變數獲取佇列，並初始化本模組的 logger
    logger = get_logger(__name__, log_queue)
    logger.info("FastAPI 應用程式啟動中...")

    # 初始化 WebSocket 管理器並將其儲存在應用程式狀態中
    app.state.manager = ConnectionManager(logger)

    if result_queue:
        asyncio.create_task(process_results())
        logger.info("結果處理背景任務已成功啟動。")
    else:
        logger.error("結果佇列 (result_queue) 未被初始化！背景任務無法啟動。")

# --- API 端點 ---
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return "<h1>歡迎來到鳳凰轉寫服務 API</h1>"

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    處理檔案上傳，產生一個唯一的任務 ID，並將任務加入佇列。
    """
    try:
        job_id = str(uuid.uuid4())
        filepath = UPLOAD_DIR / f"{job_id}_{file.filename}"

        async with aiofiles.open(filepath, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)

        logger.info(f"檔案 '{file.filename}' 已成功上傳至 '{filepath}'，任務 ID: {job_id}")

        if task_queue:
            task = {"job_id": job_id, "audio_path": str(filepath)}
            task_queue.put(task)
            logger.info(f"已將轉寫任務加入佇列: {task}")
            return JSONResponse(content={"status": "processing", "filename": file.filename, "job_id": job_id})
        else:
            logger.error("任務佇列 (task_queue) 未被初始化！無法新增任務。")
            return JSONResponse(content={"status": "error", "detail": "後端服務尚未準備就緒"}, status_code=503)

    except Exception as e:
        logger.error(f"檔案上傳或任務分派過程中發生錯誤: {e}", exc_info=True)
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=500)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 通訊端點，用於即時更新進度與結果。
    """
    manager = app.state.manager
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("客戶端 WebSocket 主動斷開連線。")
    except Exception as e:
        logger.error(f"WebSocket 連線中發生未預期錯誤: {e}", exc_info=True)
        if 'manager' in locals():
            manager.disconnect(websocket)


# --- 掛載靜態檔案 ---
# 這行必須放在後面，以免覆蓋 '/' 等 API 端點
app.mount("/", StaticFiles(directory="static", html=True), name="static")
