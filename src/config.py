# src/config.py
from pydantic import BaseModel

class WebSocketConfig(BaseModel):
    """WebSocket 伺服器設定"""
    host: str = "127.0.0.1"
    port: int = 8000

class ModelConfig(BaseModel):
    """模型設定"""
    size: str = "tiny"
    beam_size: int = 1
    language: str | None = None

class BaseConfig(BaseModel):
    """基礎設定"""
    websocket: WebSocketConfig = WebSocketConfig()
    model: ModelConfig = ModelConfig()

class TestingConfig(BaseConfig):
    """測試配置"""
    profile_name: str = "測試模式 (Testing)"
    model: ModelConfig = ModelConfig(size="tiny", beam_size=1)

class ProductionConfig(BaseConfig):
    """生產配置"""
    profile_name: str = "生產模式 (Production)"
    model: ModelConfig = ModelConfig(size="medium", beam_size=5)

_PROFILES = {
    "testing": TestingConfig,
    "production": ProductionConfig,
}

def get_config(profile_name: str = "testing") -> BaseConfig:
    """
    根據指定的 profile 名稱獲取對應的設定實例。
    """
    profile_key = profile_name.lower()
    config_class = _PROFILES.get(profile_key)

    if not config_class:
        raise ValueError(f"未知的設定檔: '{profile_name}'. 可用選項: {list(_PROFILES.keys())}")

    return config_class()
