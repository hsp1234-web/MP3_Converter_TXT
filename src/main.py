# src/main.py

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path # 導入 pathlib

from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# 導入我們的狀態管理器和轉錄工作核心
from src import model_state
from src.transcriber_worker import process_audio_file

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 路徑優化 ---
# 使用 pathlib 定義專案的根目錄和靜態檔案目錄
# 這比使用相對字串路徑 "static/index.html" 更安全、更清晰
APP_DIR = Path(__file__).parent.parent
STATIC_DIR = APP_DIR / "static"
ASSETS_DIR = APP_DIR / "assets"
# --- 優化結束 ---


def load_model():
    """
    這是一個同步的、耗時的模型載入函數。
    注意：此函數將在一個單獨的執行緒中運行，以避免阻塞 FastAPI 的主事件循環。
    """
    try:
        logger.info("背景任務：開始載入 Whisper 模型...")
        model_state.current_status = model_state.ModelStatus.LOADING

        from src.transcriber_worker import load_model as load_whisper_model
        model = load_whisper_model()

        model_state.model_instance = model
        model_state.current_status = model_state.ModelStatus.READY
        logger.info("背景任務：Whisper 模型載入成功，狀態已更新為 READY。")

    except Exception as e:
        model_state.current_status = model_state.ModelStatus.ERROR
        logger.error(f"背景任務：模型載入失敗: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 的生命週期管理器。
    """
    logger.info("FastAPI 服務啟動...")
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, load_model)
    yield
    logger.info("FastAPI 服務關閉。")


app = FastAPI(lifespan=lifespan)

# --- API 端點 (Endpoints) ---

@app.get("/", response_class=HTMLResponse)
async def get_root():
    """提供前端主頁面"""
    index_path = STATIC_DIR / "index.html"
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        logger.error(f"錯誤：找不到 index.html 於路徑 {index_path}")
        raise HTTPException(status_code=404, detail="index.html not found")

@app.get("/api/status")
async def get_status():
    """提供模型當前狀態的 API"""
    return JSONResponse(content={"status": model_state.current_status.value})

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile, background_tasks: BackgroundTasks):
    """
    接收音訊檔案並進行轉錄的 API。
    """
    if model_state.current_status != model_state.ModelStatus.READY:
        logger.warning("收到轉錄請求，但模型尚未準備就緒。")
        raise HTTPException(status_code=503, detail="服務暫時不可用，模型正在載入中。")

    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供檔案。")

    logger.info(f"收到檔案: {file.filename}")

    background_tasks.add_task(process_audio_file, file, model_state.model_instance)

    return JSONResponse(content={"message": f"檔案 '{file.filename}' 已接收並開始處理。"})

# 掛載靜態檔案目錄
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
