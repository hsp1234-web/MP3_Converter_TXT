import multiprocessing

# 使用 Manager 創建可在行程間共享的佇列
manager = multiprocessing.Manager()
task_queue = manager.Queue()
result_queue = manager.Queue()
