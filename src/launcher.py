import uvicorn
import multiprocessing
from src.mock_worker import run_mock_worker
from src.queues import task_queue, result_queue # 導入共享的佇列

import os

def run_fastapi_server():
    """啟動 FastAPI 伺服器"""
    print("🚀 [主行程] 正在啟動 FastAPI 伺服器...")
    # 注意：此處不能用 reload=True，因為它會產生子行程，與我們自己的多行程管理衝突
    uvicorn.run("main:app", host="0.0.0.0", port=8000, app_dir=os.path.abspath("src"))

if __name__ == "__main__":
    print("🔥 鳳凰轉錄儀 - 模擬作戰程序開始...")

    # 建立主行程與模擬工人行程
    # 將佇列作為參數傳遞給目標函式
    main_process = multiprocessing.Process(target=run_fastapi_server)
    worker_process = multiprocessing.Process(target=run_mock_worker, args=(task_queue, result_queue))

    # 啟動行程
    main_process.start()
    worker_process.start()

    print("✅ 所有行程已成功啟動。")

    main_process.join()
    worker_process.join()

    print("🛑 所有行程已關閉。")
