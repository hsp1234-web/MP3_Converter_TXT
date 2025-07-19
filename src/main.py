import os
from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.responses import HTMLResponse
import asyncio
import uuid
from .queues import task_queue, result_queue

app = FastAPI(title="鳳凰轉錄儀後端")

# 讀取前端 HTML 內容
try:
    # 取得目前檔案的目錄
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 建立 index.html 的絕對路徑
    html_path = os.path.join(current_dir, '..', 'static', 'index.html')
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
except FileNotFoundError:
    html_content = "<h1>錯誤：找不到 index.html</h1>"

@app.get("/", response_class=HTMLResponse)
async def get_root():
    return HTMLResponse(content=html_content)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    # 未來邏輯：可先將檔案暫存
    print(f"收到檔案: {file.filename}，分配任務 ID: {job_id}")
    # 將任務（ID 和檔名）放入任務佇列
    task_queue.put((job_id, file.filename))
    return {"message": "任務已加入佇列", "job_id": job_id}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    print(f"WebSocket 客戶端 {client_id} 已連線")
    try:
        while True:
            # 檢查結果佇列中是否有新訊息
            if not result_queue.empty():
                result = result_queue.get()
                await websocket.send_json(result)
            await asyncio.sleep(0.1) # 短暫休眠，避免 CPU 空轉
    except Exception as e:
        print(f"WebSocket 客戶端 {client_id} 已斷線: {e}")
