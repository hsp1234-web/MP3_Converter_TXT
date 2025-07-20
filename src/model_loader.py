# src/model_loader.py
from faster_whisper import WhisperModel
from src.config import BaseConfig
from src.utils.hardware import get_best_hardware_config
from src.logging_config import get_logger

logger = get_logger(__name__)

def load_model(config: BaseConfig) -> WhisperModel:
    """
    根據設定載入 faster-whisper 模型。
    """
    hardware_config = get_best_hardware_config()
    logger.info(f"正在載入模型: {config.model.size}")
    logger.info(f"使用硬體設定: {hardware_config}")

    try:
        model = WhisperModel(
            config.model.size,
            device=hardware_config["device"],
            compute_type=hardware_config["compute_type"]
        )
        logger.info("模型載入成功。")
        return model
    except Exception as e:
        logger.error(f"模型載入失敗: {e}", exc_info=True)
        raise
