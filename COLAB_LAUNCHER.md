#@title 🚀 2. 啟動鳳凰專案伺服器
#@markdown ---
#@markdown ### **請先執行第一個儲存格，再執行此儲存格。**
#@markdown ---
#@markdown **作戰配置選擇:**
PROFILE = "testing" #@param ["testing", "production"]
#@markdown ---
#@markdown **專案資料夾名稱:**
#@markdown <small>*(注意：此處的名稱必須與第一個儲存格中的 `DESTINATION_FOLDER_NAME` 完全一致)*</small>
DESTINATION_FOLDER_NAME = "\u9CF3\u51F0\u8F49\u9304\u5100\u7A0B\u5F0F\u78BC" #@param {type:"string"}
#@markdown ---

import os
import sys
import time
import subprocess
from pathlib import Path
from IPython.display import display, HTML

# --- 核心變數與路徑設定 ---
PROJECT_PATH = Path(f"/content/{DESTINATION_FOLDER_NAME}")
COMMANDER_CONSOLE_PATH = PROJECT_PATH / "commander_console.py"
LOG_FILE_PATH = PROJECT_PATH / "phoenix_transcriber.log"
PYTHON_EXECUTABLE = sys.executable

# --- 前置檢查 ---
if not PROJECT_PATH.is_dir():
    print(f"❌ 錯誤：找不到專案資料夾 '{PROJECT_PATH}'")
    print("👉 請確認您已經成功執行第一個儲存格，並且上面的 'DESTINATION_FOLDER_NAME' 變數設定正確。")
else:
    print(f"✅ 成功找到專案資料夾: {PROJECT_PATH}")
    os.chdir(PROJECT_PATH)
    print(f"✅ 已將工作目錄切換至: {os.getcwd()}")

    server_process = None
    try:
        # --- 1. 安裝/更新依賴 ---
        print("\n--- 步驟 1: 安裝/更新依賴套件 ---")
        install_deps_command = [
            PYTHON_EXECUTABLE,
            str(COMMANDER_CONSOLE_PATH),
            "install-deps"
        ]
        subprocess.run(install_deps_command, check=True, capture_output=True, text=True)
        print("✅ 依賴套件已成功安裝。")

        # --- 2. 啟動伺服器 (背景執行) ---
        print(f"\n--- 步驟 2: 以 '{PROFILE}' 配置啟動伺服器 ---")
        run_server_command = [
            PYTHON_EXECUTABLE,
            str(COMMANDER_CONSOLE_PATH),
            "run-server",
            "--profile",
            PROFILE
        ]
        # 使用 Popen 在背景啟動伺服器
        server_process = subprocess.Popen(
            run_server_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )
        print("⏳ 伺服器正在背景啟動中，請稍候...")

        # --- 3. 監控日誌以確認啟動成功 ---
        start_time = time.time()
        log_monitoring_timeout = 60 # seconds
        server_ready = False

        # 等待日誌檔案被創建
        while not LOG_FILE_PATH.exists() and time.time() - start_time < log_monitoring_timeout:
            time.sleep(1)

        if not LOG_FILE_PATH.exists():
             print("❌ 錯誤：等待日誌檔案創建超時。")
             print(f"👉 請檢查 '{LOG_FILE_PATH}' 是否有寫入權限。")
        else:
            print(f"✅ 成功找到日誌檔案: {LOG_FILE_PATH}")
            print("⏳ 正在監控日誌以確認 Uvicorn 服務是否成功運行...")
            with open(LOG_FILE_PATH, 'r') as log_file:
                while time.time() - start_time < log_monitoring_timeout:
                    line = log_file.readline()
                    if not line:
                        time.sleep(0.5)
                        continue
                    print(f"   [日誌] {line.strip()}")
                    if "Uvicorn running on" in line:
                        print("\n✅ 偵測到 Uvicorn 成功啟動！")
                        server_ready = True
                        break
                    if "ERROR" in line.upper() or "Traceback" in line:
                        print("❌ 錯誤：伺服器啟動失敗，請檢查日誌輸出。")
                        break

        # --- 4. 生成並顯示公開網址 ---
        if server_ready:
            from google.colab.output import eval_js
            public_url = eval_js('google.colab.kernel.proxyPort(8000)')
            print("\n--- 步驟 3: 生成公開網址 ---")
            display(HTML(f"""
            <div style="border: 2px solid #4CAF50; padding: 15px; border-radius: 10px; background-color: #f0fff0;">
                <h2 style="color: #4CAF50;">🎉 伺服器已成功啟動！</h2>
                <p>您可以透過以下公開網址存取服務：</p>
                <a href="{public_url}" target="_blank" style="font-size: 16px; font-weight: bold;">{public_url}</a>
                <p style="margin-top: 15px; font-size: 12px; color: #555;">
                (這個儲存格會持續運行以保持伺服器開啟，您可以隨時手動中斷它來關閉伺服器)
                </p>
            </div>
            """))

            # 保持儲存格運行
            while True:
                time.sleep(3600)
        else:
            print("\n❌ 伺服器啟動失敗，無法生成公開網址。")
            print("👉 請向上捲動查看日誌輸出以了解錯誤詳情。")

    except subprocess.CalledProcessError as e:
        print(f"❌ 執行命令時發生錯誤: {e.cmd}")
        print(f"   返回碼: {e.returncode}")
        print(f"   輸出:\n{e.stdout}")
        print(f"   錯誤輸出:\n{e.stderr}")
    except KeyboardInterrupt:
        print("\n🛑 收到使用者中斷信號，正在關閉伺服器...")
    except Exception as e:
        print(f"❌ 發生未預期的錯誤: {e}")
    finally:
        if server_process:
            print("⏳ 正在終止背景伺服器行程...")
            server_process.terminate()
            server_process.wait(timeout=10)
            if server_process.poll() is None:
                print("⚠️ 伺服器行程未在10秒內終止，將強制終止。")
                server_process.kill()
            print("✅ 伺服器已成功關閉。")
