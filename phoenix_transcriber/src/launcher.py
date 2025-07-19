import uvicorn
import multiprocessing
from src.transcriber_worker import run_transcriber_worker

def run_fastapi_server(task_queue, result_queue, file_event):
    from src.main import app
    app.state.task_queue = task_queue
    app.state.result_queue = result_queue
    app.state.file_event = file_event
    print("🚀 [主行程] 正在啟動 FastAPI 伺服器...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    print("🔥 鳳凰轉錄儀 - 最終版啟動程序開始...")
    manager = multiprocessing.Manager()
    task_q = manager.Queue()
    result_q = manager.Queue()
    file_event = manager.Event()

    main_process = multiprocessing.Process(target=run_fastapi_server, args=(task_q, result_q, file_event))
    worker_process = multiprocessing.Process(target=run_transcriber_worker, args=(task_q, result_q, file_event))

    main_process.start()
    worker_process.start()
    print("✅ 所有行程已成功啟動。")

    main_process.join()
    worker_process.join()
    print("🛑 所有行程已關閉。")
