# -*- coding: utf-8 -*-

"""
鳳凰轉錄儀 - 作戰設定檔 (Phoenix Transcriber - Tactical Configuration)

此檔案定義了不同作戰情境下的系統設定。
Jules 應根據任務需求，在此處調整或新增配置。
"""

class BaseConfig:
    """基礎設定，所有配置都應繼承自此類別。"""
    # WebSocket 伺服器設定
    WEBSOCKET_HOST = "127.0.0.1"
    WEBSOCKET_PORT = 8000

    # 預設模型設定
    MODEL_SIZE = "tiny"
    BEAM_SIZE = 1
    LANGUAGE = None  # 自動偵測

class TestingConfig(BaseConfig):
    """
    測試配置 (Testing Profile)
    - 使用極小模型，以利於快速啟動與驗證。
    - 適用於開發、除錯及自動化整合測試。
    """
    PROFILE_NAME = "測試模式 (Testing)"
    MODEL_SIZE = "tiny"
    BEAM_SIZE = 1

class ProductionConfig(BaseConfig):
    """
    生產配置 (Production Profile)
    - 使用效能與品質均衡的模型。
    - 適用於正式作戰部署。
    - 注意：'medium' 模型需要較多資源，請確保硬體規格足夠。
    """
    PROFILE_NAME = "生產模式 (Production)"
    MODEL_SIZE = "medium"
    BEAM_SIZE = 5

# --- 設定檔選擇邏輯 ---

# 建立一個 profile 名稱到設定類別的映射
_PROFILES = {
    "testing": TestingConfig,
    "production": ProductionConfig,
}

def get_config(profile_name: str = "testing"):
    """
    根據指定的 profile 名稱獲取對應的設定實例。

    Args:
        profile_name (str): 配置檔案的名稱 (例如 "testing", "production")。
                            不區分大小寫。

    Returns:
        An instance of a config class (e.g., TestingConfig).

    Raises:
        ValueError: If the profile_name is not found.
    """
    profile_key = profile_name.lower()
    config_class = _PROFILES.get(profile_key)

    if not config_class:
        raise ValueError(f"未知的設定檔: '{profile_name}'. 可用選項: {list(_PROFILES.keys())}")

    return config_class()

# --- 使用範例 ---
if __name__ == '__main__':
    # 獲取預設的測試設定
    test_config = get_config()
    print(f"--- {test_config.PROFILE_NAME} ---")
    print(f"模型大小: {test_config.MODEL_SIZE}")
    print(f"Beam Size: {test_config.BEAM_SIZE}")
    print(f"WebSocket: ws://{test_config.WEBSOCKET_HOST}:{test_config.WEBSOCKET_PORT}")

    print("\n" + "="*30 + "\n")

    # 獲取生產設定
    try:
        prod_config = get_config("production")
        print(f"--- {prod_config.PROFILE_NAME} ---")
        print(f"模型大小: {prod_config.MODEL_SIZE}")
        print(f"Beam Size: {prod_config.BEAM_SIZE}")
    except ValueError as e:
        print(e)

    print("\n" + "="*30 + "\n")

    # 測試無效的設定
    try:
        invalid_config = get_config("invalid_profile")
    except ValueError as e:
        print(f"成功捕捉到錯誤: {e}")
