import uvicorn
import multiprocessing
import time

def run_fastapi():
    """啟動 FastAPI 伺服器"""
    print("🚀 [主行程] 正在啟動 FastAPI 伺服器...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, app_dir="src")

def run_worker():
    """啟動轉錄工人行程"""
    print("🛠️ [工人行程] 正在啟動...")
    # 此處將是 transcriber_worker.py 的主要邏輯入口
    # 為了測試，我們先讓它模擬工作
    time.sleep(999) # 保持行程運行
    print("✅ [工人行程] 已關閉。")


if __name__ == "__main__":
    print("🔥 鳳凰轉錄儀 - 全面啟動程序開始...")

    # 建立主行程與工人行程
    main_process = multiprocessing.Process(target=run_fastapi)
    worker_process = multiprocessing.Process(target=run_worker)

    # 啟動行程
    main_process.start()
    worker_process.start()

    print("✅ 所有行程已成功啟動。")

    # 等待行程結束
    main_process.join()
    worker_process.join()

    print("🛑 所有行程已關閉。")
