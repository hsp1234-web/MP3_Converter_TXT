import time
import queue
import logging
from multiprocessing import Queue
from threading import Thread

# 設定日誌
logging.basicConfig(level=logging.INFO, format='[模擬工人] %(asctime)s - %(message)s')

def worker_process(task_queue: Queue, result_queue: Queue):
    """
    模擬一個在背景處理任務的工人行程。
    """
    logging.info("模擬工人行程已啟動。")
    while True:
        try:
            # 從任務佇列中獲取任務，如果佇列為空，則阻塞等待
            # 設置 timeout 可以在佇列長時間為空時做其他事，例如檢查退出信號
            task = task_queue.get(timeout=1.0)
            if task is None:
                logging.info("收到結束信號，工人行程即將關閉。")
                break

            filepath = task.get("filepath")
            logging.info(f"開始處理檔案: {filepath}")

            # 模擬一個耗時的轉寫過程
            total_steps = 10
            for i in range(total_steps):
                progress = (i + 1) / total_steps
                # 將進度訊息放入結果佇列
                result_queue.put({
                    "type": "progress",
                    "progress": progress,
                    "message": f"正在分析音檔的第 {i+1}/{total_steps} 部分..."
                })
                time.sleep(0.1) # 在自動化測試中，縮短延遲時間

            # 模擬最終的轉寫結果
            transcript = f"這是檔案 '{filepath}' 的模擬轉寫結果。\n" \
                         f"時間戳: {time.strftime('%Y-%m-%d %H:%M:%S')}"

            # 將最終結果放入結果佇列
            result_queue.put({
                "type": "result",
                "transcript": transcript
            })
            logging.info(f"完成處理檔案: {filepath}")

        except queue.Empty:
            # 當佇列在 timeout 時間內為空時，會拋出此異常
            # 這是正常的，讓我們可以繼續循環，檢查退出信號等
            continue
        except Exception as e:
            logging.error(f"處理任務時發生錯誤: {e}", exc_info=True)
            # (可選) 向結果佇列報告錯誤
            result_queue.put({
                "type": "error",
                "message": str(e)
            })

    logging.info("模擬工人行程已關閉。")
