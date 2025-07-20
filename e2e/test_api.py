# e2e/test_api.py
import requests

def test_server_is_alive(live_api_server):
    """
    一個極簡測試，只用來驗證 live_api_server fixture 能否成功啟動。
    """
    # live_api_server fixture 會被 pytest 自動傳入
    # 如果測試能執行到這裡，代表伺服器已成功啟動

    # 我們對伺服器的根 URL 發出一個請求
    response = requests.get(f"{live_api_server}/")

    # 斷言伺服器返回了成功的狀態碼
    assert response.status_code == 200
    print(f"\n✅ 最小化 E2E 測試成功：成功從 {live_api_server}/ 獲取回應。")
