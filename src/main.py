import asyncio
import logging
import aiofiles
from pathlib import Path
from multiprocessing import Queue
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# --- 常數與設定 ---
# 建立存放上傳檔案的目錄
UPLOAD_DIR = Path("IN")
UPLOAD_DIR.mkdir(exist_ok=True)

# 設定日誌
logging.basicConfig(level=logging.INFO, format='[主應用] %(asctime)s - %(levelname)s - %(message)s')

# --- FastAPI 應用程式實例 ---
app = FastAPI()

# --- 全域變數 ---
# 這不是生產環境的最佳實踐，但在這個模擬中，我們用它來從啟動器接收佇列
# 在真實應用中，可以考慮使用更穩定的依賴注入系統或應用程式狀態
task_queue: Queue = None
result_queue: Queue = None

# --- WebSocket 管理 ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info("一個新的 WebSocket 客戶端已連線。")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logging.info("一個 WebSocket 客戶端已離線。")

    async def broadcast(self, message: dict):
        """向所有連線的客戶端廣播訊息"""
        # 為了安全，我們複製一份連線列表來迭代
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logging.warning(f"向客戶端傳送訊息失敗: {e}, 可能客戶端已非正常關閉。")


manager = ConnectionManager()

# --- 背景任務 ---
async def process_results():
    """
    一個非同步的背景任務，持續從結果佇列中讀取訊息並透過 WebSocket 廣播。
    """
    logging.info("結果處理迴圈已啟動。")
    loop = asyncio.get_running_loop()
    while True:
        if not result_queue.empty():
            try:
                # 使用 run_in_executor 來非阻塞地獲取佇列中的項目
                result = await loop.run_in_executor(None, result_queue.get)
                logging.info(f"從結果佇列收到訊息: {result}")
                await manager.broadcast(result)
            except Exception as e:
                logging.error(f"處理結果佇列時發生錯誤: {e}", exc_info=True)
        await asyncio.sleep(0.1) # 避免過度佔用 CPU

# --- FastAPI 事件處理 ---
@app.on_event("startup")
async def startup_event():
    # 在應用啟動時，啟動背景任務
    # 確保 result_queue 已經被 launcher 賦值
    if result_queue:
        asyncio.create_task(process_results())
    else:
        logging.error("結果佇列 (result_queue) 未被初始化！背景任務無法啟動。")

# --- API 端點 ---
@app.get("/", response_class=HTMLResponse)
async def read_root():
    # 由於我們掛載了 static 目錄，這個端點主要用於 API 確認
    # 實際上，FastAPI 會先在 static 目錄尋找 index.html
    return "<h1>歡迎來到鳳凰轉寫服務 API</h1>"


import uuid

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    處理檔案上傳，產生一個唯一的任務 ID，並將任務加入佇列。
    """
    try:
        job_id = str(uuid.uuid4())
        filepath = UPLOAD_DIR / f"{job_id}_{file.filename}"

        # 使用 aiofiles 進行非同步檔案寫入
        async with aiofiles.open(filepath, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)

        logging.info(f"檔案 '{file.filename}' 已成功上傳至 '{filepath}'，任務 ID: {job_id}")

        # 檢查任務佇列是否可用
        if task_queue:
            # 建立符合工人期望的任務字典
            task = {
                "job_id": job_id,
                "audio_path": str(filepath)
            }
            task_queue.put(task)
            logging.info(f"已將轉寫任務加入佇列: {task}")
            return JSONResponse(content={"status": "processing", "filename": file.filename, "job_id": job_id})
        else:
            logging.error("任務佇列 (task_queue) 未被初始化！無法新增任務。")
            return JSONResponse(content={"status": "error", "detail": "後端服務尚未準備就緒"}, status_code=503)

    except Exception as e:
        logging.error(f"檔案上傳或任務分派過程中發生錯誤: {e}", exc_info=True)
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=500)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 通訊端點，用於即時更新進度與結果。
    """
    await manager.connect(websocket)
    try:
        # 保持連線開啟狀態，直到客戶端離線
        while True:
            # 我們主要透過廣播發送訊息，所以這裡只是保持連線
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logging.info("客戶端 WebSocket 主動斷開連線。")
    except Exception as e:
        logging.error(f"WebSocket 連線中發生未預期錯誤: {e}")
        manager.disconnect(websocket)


# --- 掛載靜態檔案 ---
# 這行必須放在後面，以免覆蓋 '/' 等 API 端點
app.mount("/", StaticFiles(directory="static", html=True), name="static")
