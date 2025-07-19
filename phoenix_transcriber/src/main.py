import os
import shutil
import uuid
import asyncio
from fastapi import FastAPI, Request, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from src import config

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    os.makedirs(config.IN_DIR, exist_ok=True)
    os.makedirs(config.OUT_DIR, exist_ok=True)
    # 啟動一個背景任務來監聽結果佇列
    asyncio.create_task(listen_for_results())

async def listen_for_results():
    result_queue = app.state.result_queue
    while True:
        if not result_queue.empty():
            result = result_queue.get()
            await manager.broadcast(result)
        await asyncio.sleep(0.1)

@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    task_queue = request.app.state.task_queue
    file_event = request.app.state.file_event
    job_id = str(uuid.uuid4())

    file_location = os.path.join(config.IN_DIR, file.filename)
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    task_queue.put((job_id, file.filename))
    file_event.set() # 通知工人有新檔案
    await manager.broadcast({"job_id": job_id, "filename": file.filename, "status": "queued"})
    return {"message": "檔案已加入佇列", "job_id": job_id}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
