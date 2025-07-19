import multiprocessing as mp
from src.logger import get_logger

def transcriber_worker_process(log_queue: mp.Queue, task_queue: mp.Queue, result_queue: mp.Queue, config):
    from faster_whisper import WhisperModel
    from src.core.hardware import get_best_hardware_config
    """
    轉錄工人行程的主循環。

    這個函數在一個獨立的行程中運行，負責：
    1.  監聽任務佇列。
    2.  在收到任務後，呼叫 `transcribe_job` 執行實際的轉錄工作。
    3.  處理行程的啟動、關閉和錯誤。
    """
    # 在子行程中，使用傳入的佇列來設定 logger
    logger = get_logger("轉錄工人", log_queue)
    logger.info(f"工人行程已啟動，使用模型: {config.MODEL_SIZE}, Beam Size: {config.BEAM_SIZE}")

    # 載入模型一次，供所有任務重複使用
    try:
        hardware_config = get_best_hardware_config()
        logger.info(f"偵測到最佳硬體設定: {hardware_config}")
        model = WhisperModel(
            config.MODEL_SIZE,
            device=hardware_config["device"],
            compute_type=hardware_config["compute_type"]
        )
        logger.info("模型載入成功，工人準備就緒。")
    except Exception as e:
        logger.error(f"模型載入失敗，工人行程無法啟動: {e}", exc_info=True)
        return # 模型載入失敗，行程無法工作，直接退出

    while True:
        try:
            # 從隊列中獲取任務，這是一個阻塞操作
            job = task_queue.get()

            # "毒丸" 協議：收到 None 時，工人進程結束
            if job is None:
                logger.info("收到結束信號，工人行程即將關閉。")
                break

            job_id = job.get("job_id")
            audio_path = job.get("audio_path")
            logger.info(f"收到新任務: Job ID {job_id}, 音檔: {audio_path}")

            # 呼叫處理單個任務的函數
            transcribe_job(
                logger=logger,
                result_queue=result_queue,
                job_id=job_id,
                audio_path=audio_path,
                model=model, # 傳入已載入的模型
                beam_size=config.BEAM_SIZE,
                language=config.LANGUAGE
            )

        except Exception as e:
            # 這是主循環的捕獲，用於處理佇列 get 或其他意外錯誤
            logger.error(f"工人在主循環中發生嚴重錯誤: {e}", exc_info=True)


def transcribe_job(logger, result_queue, job_id, audio_path, model, beam_size, language):
    """
    執行單個轉錄任務的函數。

    Args:
        logger: 日誌記錄器實例。
        result_queue: 用於回報結果和進度的佇列。
        job_id (str): 任務的唯一標識符。
        audio_path (str): 音訊檔案路徑。
        model: 已載入的 faster-whisper 模型實例。
        beam_size (int): 解碼時的 beam size。
        language (str, optional): 音訊語言代碼。
    """
    try:
        # 1. 報告進度：開始處理
        result_queue.put({"status": "processing", "job_id": job_id, "progress": 10, "message": "開始轉錄..."})

        # 2. 執行轉錄
        segments, info = model.transcribe(
            audio_path,
            beam_size=beam_size,
            language=language,
        )

        detected_lang = info.language
        lang_prob = info.language_probability
        logger.info(f"任務 {job_id}: 偵測到語言 '{detected_lang}' (可信度: {lang_prob:.2f})，音訊時長: {info.duration:.2f}s")
        result_queue.put({"status": "processing", "job_id": job_id, "progress": 50, "message": f"偵測到語言: {detected_lang} (可信度: {lang_prob:.2f})"})

        # 3. 組合轉錄結果
        full_transcript = "".join(segment.text for segment in segments)
        logger.info(f"任務 {job_id}: 轉錄完成。")

        # 4. 報告最終結果
        result = {
            "status": "completed",
            "job_id": job_id,
            "transcript": full_transcript.strip(),
            "language": detected_lang,
            "duration": info.duration
        }
        result_queue.put(result)

    except Exception as e:
        error_message = f"轉錄任務 {job_id} 過程中發生錯誤: {e}"
        logger.error(error_message, exc_info=True)
        result_queue.put({"status": "error", "job_id": job_id, "message": str(e)})
