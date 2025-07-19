import time
from faster_whisper import WhisperModel
from src.core.hardware import get_best_hardware_config

def transcribe_worker(queue, job_id, audio_path, model_size="tiny", beam_size=1, language=None):
    """
    真實的轉錄工人，使用 faster-whisper 進行語音轉錄。

    Args:
        queue: 用於與主進程通信的隊列。
        job_id (str): 此轉錄任務的唯一標識符。
        audio_path (str): 要轉錄的音訊檔案路徑。
        model_size (str): 要使用的 Whisper 模型大小 (例如 "tiny", "medium")。
        beam_size (int): Beam size for decoding.
        language (str, optional): 音訊的語言代碼 (例如 "en", "zh")。如果為 None，則自動偵測。
    """
    try:
        # 1. 報告進度：正在初始化
        queue.put({"status": "processing", "job_id": job_id, "progress": 0, "message": "正在初始化轉錄工人..."})

        # 2. 獲取硬體設定並載入模型
        hardware_config = get_best_hardware_config()
        device = hardware_config["device"]
        compute_type = hardware_config["compute_type"]

        queue.put({"status": "processing", "job_id": job_id, "progress": 10, "message": f"使用硬體設定: {hardware_config}"})

        # 在 CPU 上執行時，可以設定線程數以優化效能
        # model = WhisperModel(model_size, device=device, compute_type=compute_type, cpu_threads=4)
        model = WhisperModel(model_size, device=device, compute_type=compute_type)

        queue.put({"status": "processing", "job_id": job_id, "progress": 30, "message": "模型載入完成，開始轉錄..."})

        # 3. 執行轉錄
        # NOTE: faster-whisper 的 transcribe 方法是一個 generator，會回傳一個包含 segments 的 iterator。
        # 為了簡單起見，我們一次性處理所有 segments。
        segments, info = model.transcribe(
            audio_path,
            beam_size=beam_size,
            language=language,
            # vad_filter=True, # 語音活動檢測
            # vad_parameters=dict(min_silence_duration_ms=500),
        )

        detected_lang = info.language
        lang_prob = info.language_probability

        queue.put({"status": "processing", "job_id": job_id, "progress": 50, "message": f"偵測到語言: {detected_lang} (可信度: {lang_prob:.2f})"})

        full_transcript = ""
        # 這裡我們可以逐步回報進度，但為了簡化，我們先在迴圈後一次性回報
        for segment in segments:
            full_transcript += segment.text
            # 可以在此處 put 每個 segment 的進度
            # progress = (segment.end / info.duration) * 100
            # queue.put(...)

        # 4. 報告最終結果
        result = {
            "status": "completed",
            "job_id": job_id,
            "transcript": full_transcript.strip(),
            "language": detected_lang,
            "duration": info.duration
        }
        queue.put(result)

    except Exception as e:
        # 報告錯誤
        error_message = f"轉錄過程中發生錯誤: {e}"
        print(error_message)
        queue.put({"status": "error", "job_id": job_id, "message": error_message})

    finally:
        # 5. 釋放資源 (雖然 Python 會自動回收，但這是一個好習慣)
        # 在這個架構中，worker process 結束後記憶體會自動釋放，
        # 所以不需要手動 del model 或 torch.cuda.empty_cache()。
        # print(f"任務 {job_id} 完成，工人進程即將退出。")
        pass
