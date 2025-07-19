import time
import random

def run_mock_worker(task_queue, result_queue):
    """
    模擬轉錄工人的主函式。
    從任務佇列接收任務，模擬處理，然後將結果放入結果佇列。
    """
    print("🛠️ [模擬工人] 已啟動，等待任務...")
    while True:
        try:
            # 從佇列中獲取任務，如果沒有任務會阻塞等待
            job_id, filename = task_queue.get()
            print(f"🛠️ [模擬工人] 收到任務 {job_id}，處理檔案: {filename}")

            # 1. 回報進度：處理中
            result_queue.put({"job_id": job_id, "type": "progress", "message": f"開始處理檔案: {filename}"})

            # 2. 模擬轉錄耗時
            time.sleep(random.uniform(2, 5))

            # 3. 產生假的轉錄結果
            mock_transcript = f"--- {filename} 的模擬轉錄結果 ---\n[00:00:01.123] 這是由模擬工人產生的結果。\n[00:00:08.456] 系統流程已成功驗證。\n"

            # 4. 回報進度：完成
            result_queue.put({"job_id": job_id, "type": "result", "transcript": mock_transcript})
            print(f"✅ [模擬工人] 完成任務 {job_id}")

        except Exception as e:
            print(f"❌ [模擬工人] 發生錯誤: {e}")
            # 向主進程回報錯誤
            result_queue.put({"job_id": job_id, "type": "error", "message": str(e)})
