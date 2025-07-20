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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 的生命週期管理器。
    在伺服器啟動時載入模型，在關閉時清理。
    """
    logger.info("FastAPI 服務啟動...")
    model_state.current_status = model_state.ModelStatus.LOADING
    logger.info("背景任務：開始載入 Whisper 模型...")

    try:
        from faster_whisper import WhisperModel
        from src.core.hardware import get_best_hardware_config

        hardware_config = get_best_hardware_config()
        model = WhisperModel(
            "tiny",
            device=hardware_config["device"],
            compute_type=hardware_config["compute_type"]
        )
        model_state.model_instance = model
        model_state.current_status = model_state.ModelStatus.READY
        logger.info("背景任務：Whisper 模型載入成功，狀態已更新為 READY。")
    except Exception as e:
        model_state.current_status = model_state.ModelStatus.ERROR
        logger.error(f"背景任務：模型載入失敗: {e}", exc_info=True)

    yield

    # 清理工作
    model_state.model_instance = None
    logger.info("FastAPI 服務關閉，模型已卸載。")


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
