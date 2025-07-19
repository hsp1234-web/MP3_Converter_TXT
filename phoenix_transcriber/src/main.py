from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.responses import HTMLResponse
import os
import asyncio

app = FastAPI(title="鳳凰轉錄儀後端")

# 讀取前端 HTML 內容
try:
    with open("static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
except FileNotFoundError:
    html_content = "<h1>錯誤：找不到 index.html</h1>"

@app.get("/", response_class=HTMLResponse)
async def get_root():
    """提供 Web UI 主頁面"""
    return HTMLResponse(content=html_content)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """接收上傳檔案並加入任務佇列"""
    # 未來邏輯：將任務加入 multiprocessing.Queue
    print(f"收到檔案: {file.filename}")
    return {"message": "任務已加入佇列 (模擬)", "filename": file.filename}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """處理 WebSocket 即時通訊"""
    await websocket.accept()
    print(f"WebSocket 客戶端 {client_id} 已連線")
    try:
        while True:
            # 未來邏輯：監聽來自工人的進度回報並發送給前端
            await websocket.send_json({"type": "status", "message": "系統待命中 (模擬)"})
            await asyncio.sleep(5) # 模擬心跳
    except Exception as e:
        print(f"WebSocket 客戶端 {client_id} 已斷線: {e}")
