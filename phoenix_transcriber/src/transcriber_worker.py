import os
import shutil
import time
from src import config

def setup_worker_directories():
    os.makedirs(config.IN_DIR, exist_ok=True)
    os.makedirs(config.OUT_DIR, exist_ok=True)
    os.makedirs(config.PROCESSED_DIR, exist_ok=True)

def run_transcriber_worker(task_queue, result_queue, file_event):
    print("🛠️ [工人] 正在啟動...")
    setup_worker_directories()
    print("✅ [工人] 模型 'mock' 載入成功，開始監聽任務。")

    while True:
        if task_queue.empty():
            file_event.wait(timeout=5) # 等待新檔案事件，或超時
            file_event.clear() # 清除事件，等待下次觸發
            continue

        job_id, filename = task_queue.get()
        input_path = os.path.join(config.IN_DIR, filename)
        output_filename = os.path.splitext(filename)[0] + ".txt"
        output_path = os.path.join(config.OUT_DIR, output_filename)

        try:
            result_queue.put({"job_id": job_id, "status": "processing", "message": "轉錄中..."})
            # Simulate transcription time
            time.sleep(5)

            mock_transcript = "這是一個模擬的轉錄文本。"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(mock_transcript)

            result_queue.put({"job_id": job_id, "status": "completed", "transcript": mock_transcript})
            shutil.move(input_path, os.path.join(config.PROCESSED_DIR, filename))

        except Exception as e:
            result_queue.put({"job_id": job_id, "status": "error", "message": str(e)})
