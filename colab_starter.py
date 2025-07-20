# colab_starter.py
import subprocess
import os
import time
from pyngrok import ngrok

def run_command(command, env=None):
    """在背景執行一個指令"""
    return subprocess.Popen(command, env=env)

def main():
    print("🚀 鳳凰專案 Colab 啟動器 🚀")

    # --- 1. 安裝依賴 ---
    print("\n--- 步驟 1: 安裝依賴 ---")
    subprocess.run(["pip", "install", "poetry", "pyngrok"], check=True)
    subprocess.run(["poetry", "install", "--no-root"], check=True)
    print("✅ 依賴安裝完成。")

    # --- 2. 設定 ngrok ---
    print("\n--- 步驟 2: 設定 ngrok ---")
    ngrok_auth_token = os.environ.get("NGROK_AUTH_TOKEN")
    if not ngrok_auth_token:
        print("❌ 錯誤: 請在 Colab 的 Secrets 中設定 NGROK_AUTH_TOKEN。")
        return

    ngrok.set_auth_token(ngrok_auth_token)
    print("✅ ngrok token 設定完成。")

    # --- 3. 啟動伺服器和工人 ---
    print("\n--- 步驟 3: 啟動伺服器與工人 ---")
    env = os.environ.copy()
    env["PYTHONPATH"] = "."

    # 啟動伺服器
    server_command = ["poetry", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
    server_process = run_command(server_command, env=env)
    print("🔥 FastAPI 伺服器已在背景啟動。")

    # 啟動工人
    worker_command = ["poetry", "run", "python", "commander_console.py", "run-worker"]
    worker_process = run_command(worker_command, env=env)
    print("👷 工人行程已在背景啟動。")

    # --- 4. 建立公開網址 ---
    print("\n--- 步驟 4: 建立公開網址 ---")
    time.sleep(5) # 等待伺服器啟動
    try:
        public_url = ngrok.connect(8000)
        print("\n\n🎉🎉🎉 啟動成功 🎉🎉🎉")
        print(f"你的服務現在可以透過以下網址存取:")
        print(public_url)
        print("\n你可以開始上傳音訊檔案進行轉錄了！")
    except Exception as e:
        print(f"❌ 建立 ngrok 通道時發生錯誤: {e}")

if __name__ == "__main__":
    main()
