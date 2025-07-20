# colab_starter.py
import subprocess
import os
import time
from IPython.display import display, HTML

def run_command_in_background(command, env=None):
    """在背景執行一個指令，不顯示輸出"""
    return subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def get_colab_proxy_url(port):
    """
    使用 google.colab.output.eval_js 來獲取 Colab 的代理 URL。
    增加了健壯性設計，以應對 eval_js 可能返回的不同格式。
    """
    from google.colab import output

    try:
        # 執行 JavaScript 來獲取代理資訊
        public_url_data = output.eval_js(f"google.colab.kernel.proxyPort({port})")

        # 處理返回的資料
        if isinstance(public_url_data, str):
            return public_url_data
        elif isinstance(public_url_data, dict) and public_url_data.get('url'):
            return public_url_data['url']
        else:
            # 作為備用方案，嘗試使用 serve_kernel_port_as_window
            output.serve_kernel_port_as_window(port, path='/')
            return None # 告知主程式已使用備用方案
    except Exception as e:
        print(f"❌ 獲取 Colab 代理網址時發生錯誤: {e}")
        return None


def main():
    print("🚀 鳳凰專案 Colab 啟動器 🚀")
    PORT = 8000

    # --- 1. 安裝依賴 ---
    print("\n--- 步驟 1: 安裝依賴 ---")
    # 將 poetry 安裝過程靜音，只在出錯時顯示資訊
    result = subprocess.run(["pip", "install", "poetry"], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Poetry 安裝失敗:")
        print(result.stderr)
        return

    result = subprocess.run(["poetry", "install", "--no-root"], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ 專案依賴安裝失敗:")
        print(result.stderr)
        return
    print("✅ 依賴安裝完成。")

    # --- 2. 啟動伺服器和工人 ---
    print("\n--- 步驟 2: 啟動伺服器與工人 ---")
    env = os.environ.copy()
    env["PYTHONPATH"] = "."

    # 啟動伺服器
    server_command = ["poetry", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", f"--port={PORT}"]
    server_process = run_command_in_background(server_command, env=env)
    print("🔥 FastAPI 伺服器已在背景啟動。")

    # 啟動工人
    worker_command = ["poetry", "run", "python", "commander_console.py", "run-worker"]
    worker_process = run_command_in_background(worker_command, env=env)
    print("👷 工人行程已在背景啟動。")

    # --- 3. 建立並顯示公開網址 ---
    print("\n--- 步驟 3: 建立並顯示公開網址 ---")
    print("⏳ 正在等待 Colab 分配代理網址...")
    time.sleep(5) # 等待伺服器完全啟動

    public_url = get_colab_proxy_url(PORT)

    if public_url:
        print("\n\n🎉🎉🎉 啟動成功 🎉🎉🎉")
        display(HTML(f"<h3>你的服務現在可以透過以下網址存取:</h3><p><a href='{public_url}' target='_blank'>{public_url}</a></p>"))
        print("\n你可以開始上傳音訊檔案進行轉錄了！")
    else:
        print("\n✅ 已嘗試透過 Colab 內建視窗提供服務。")


if __name__ == "__main__":
    main()
