#@title 鳳凰轉錄儀 v4.3 - Colab 一鍵部署指揮中心 (部署修正版)
#@markdown ---
#@markdown ### **1. 核心作戰參數**
#@markdown > **設定後端程式碼來源、分支與日誌偏好。**
#@markdown ---
#@markdown **後端程式碼倉庫 (REPOSITORY_URL)**
#@markdown > **請填寫您的 Git 倉庫網址。**
REPOSITORY_URL = "https://github.com/hsp1234-web/MP3_Converter_TXT" #@param {type:"string"}
#@markdown **後端版本分支 (TARGET_BRANCH)**
#@markdown > **指定要部署的作戰分支。**
TARGET_BRANCH = "fix-colab-deployment" #@param {type:"string"}
#@markdown **AI 轉錄模型大小 (MODEL_SIZE)**
#@markdown > **模型越大，效果越好，但載入和處理速度越慢。建議從 `base` 開始。**
MODEL_SIZE = "base" #@param ["tiny", "base", "small", "medium", "large-v3"]
#@markdown **日誌顯示行數上限 (LOG_DISPLAY_MAX_LINES)**
#@markdown > **設定日誌顯示偏好。Colab 介面會自動處理滾動，此設定主要為未來擴充保留。**
LOG_DISPLAY_MAX_LINES = 500 #@param {type:"integer"}
#@markdown **強制刷新後端程式碼 (FORCE_REPO_REFRESH)**
#@markdown > **勾選此項會刪除舊的程式碼，重新從 GitHub 拉取。**
FORCE_REPO_REFRESH = True #@param {type:"boolean"}

#@markdown ---
#@markdown > **準備就緒後，點擊此儲存格左側的「執行」按鈕，啟動作戰。**
#@markdown ---

# ==============================================================================
# SECTION 0: 環境初始化與核心模組導入
# ==============================================================================
import os
import sys
import subprocess
import threading
import time
import shutil
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import deque

# Colab 專用模組
from google.colab import output as colab_output
from IPython.display import display, HTML, clear_output

# --- 全域常數與設定 ---
PROJECT_NAME = REPOSITORY_URL.split('/')[-1].replace('.git', '')
PROJECT_PATH = Path(f"/content/{PROJECT_NAME}")
LOG_FILE_PATH = PROJECT_PATH / "colab_deployment.log"
LOG_ARCHIVE_DIR = Path("/content/作戰日誌歸檔")
PORT = 8000
TAIPEI_TZ = timezone(timedelta(hours=8))

# --- 全域執行緒與進程控制變數 ---
SERVER_PROCESS = None
LOG_TAILER_THREAD = None
STOP_EVENT = threading.Event()

# ==============================================================================
# SECTION 1: 日誌監控核心
# ==============================================================================

class LogTailer(threading.Thread):
    """在背景執行緒中，持續追蹤日誌檔案的變化，並將新內容打印到 Colab 控制台。"""
    def __init__(self, log_file, stop_event):
        super().__init__(daemon=True)
        self.log_file = log_file
        self.stop_event = stop_event

    def run(self):
        """執行緒主體，追蹤並打印日誌檔案。"""
        while not self.log_file.exists() and not self.stop_event.is_set():
            time.sleep(0.5)
        if self.stop_event.is_set(): return

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                f.seek(0, 2)
                while not self.stop_event.is_set():
                    line = f.readline()
                    if not line:
                        time.sleep(0.2)
                        continue
                    print(line.strip())
        except Exception as e:
            print(f"[LogTailer CRITICAL Error] 日誌監控執行緒崩潰: {e}")

# ==============================================================================
# SECTION 2: 核心執行與輔助函式
# ==============================================================================

def log_message(message):
    """將帶有時間戳的訊息寫入日誌檔案。"""
    try:
        # 確保日誌目錄存在，但這不應該是專案的主目錄
        LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            timestamp = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] [Colab 指揮中心] {message}\n")
    except Exception as e:
        # 直接打印到控制台，因為日誌系統本身可能已失敗
        print(f"[Log System CRITICAL Error] 無法寫入日誌: {e}")

def run_shell_command(cmd, cwd=".", title=""):
    """執行 shell 命令，並將其輸出逐行導向到我們的日誌系統。"""
    log_message(f"🚀 開始執行: {title}")
    log_message(f"   - 指令: {' '.join(cmd)}")
    try:
        process = subprocess.Popen(
            cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', bufsize=1
        )
        for line in iter(process.stdout.readline, ''):
            log_message(f"     [輸出] {line.strip()}")
        process.stdout.close()
        return_code = process.wait()
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, cmd)
        log_message(f"✅ 成功完成: {title}")
        return True
    except Exception as e:
        error_msg = f"命令 '{title}' 執行失敗: {e}"
        log_message(f"💥 {error_msg}")
        raise RuntimeError(error_msg)

def start_server():
    """在背景啟動主應用程式伺服器。"""
    global SERVER_PROCESS
    log_message("準備啟動鳳凰轉錄儀主程式 (launcher.py)...")
    run_command = [sys.executable, "commander_console.py", "launch"]
    log_file_handle = open(LOG_FILE_PATH, 'a', encoding='utf-8')
    SERVER_PROCESS = subprocess.Popen(
        run_command, cwd=str(PROJECT_PATH),
        stdout=log_file_handle, stderr=log_file_handle,
        preexec_fn=os.setsid
    )
    log_message(f"✅ 主程式已在背景啟動 (PID: {SERVER_PROCESS.pid})。日誌將持續更新。")
    log_message("⏳ 正在等待後端服務與 AI 模型載入，這可能需要數分鐘...")

def stop_all_services():
    """停止所有背景執行緒和伺服器進程。"""
    global SERVER_PROCESS, LOG_TAILER_THREAD
    log_message("收到終止信號，開始關閉所有作戰服務...")
    STOP_EVENT.set()
    if LOG_TAILER_THREAD and LOG_TAILER_THREAD.is_alive():
        LOG_TAILER_THREAD.join(timeout=2)
    if SERVER_PROCESS and SERVER_PROCESS.poll() is None:
        log_message(f"正在終止主服務進程組 (PGID: {os.getpgid(SERVER_PROCESS.pid)})...")
        try:
            os.killpg(os.getpgid(SERVER_PROCESS.pid), subprocess.signal.SIGTERM)
            SERVER_PROCESS.wait(timeout=10)
            log_message("主服務已溫和關閉。")
        except (subprocess.TimeoutExpired, ProcessLookupError):
            log_message("溫和關閉失敗，採取強制終止...")
            try:
                os.killpg(os.getpgid(SERVER_PROCESS.pid), subprocess.signal.SIGKILL)
                log_message("主服務已被強制終止。")
            except Exception as e:
                log_message(f"強制終止時發生錯誤: {e}")
        finally:
            SERVER_PROCESS = None
    log_message("所有服務已確認關閉。")

def archive_log_file():
    """歸檔本次作戰的完整日誌檔案至指定中文目錄。"""
    print("\n" + "="*80)
    print("📜 最終作戰報告：完整日誌歸檔")
    print("="*80)
    if not LOG_FILE_PATH.exists():
        print("⚠️ 未找到日誌檔案，無法進行歸檔。")
        return
    try:
        LOG_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        # 歸檔時總是保存完整日誌，以供未來分析
        log_content = LOG_FILE_PATH.read_text(encoding='utf-8')
        timestamp = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d_%H-%M-%S")
        archive_filename = f"作戰日誌_{timestamp}.log"
        archive_filepath = LOG_ARCHIVE_DIR / archive_filename
        archive_filepath.write_text(log_content, encoding='utf-8')
        print(f"✅ 完整日誌已成功歸檔至：\n   -> {archive_filepath}")
        print("\n👍 您可以從左側「檔案」面板中找到「作戰日誌歸檔」資料夾並下載此報告。")
    except Exception as e:
        print(f"💥 歸檔日誌時發生錯誤: {e}")

# ==============================================================================
# SECTION 3: 作戰主流程
# ==============================================================================
try:
    clear_output(wait=True)
    print("🔥 鳳凰轉錄儀 v4.3 - 部署修正版 🔥")
    print("="*80)

    # --- 步驟 0: 清理舊環境 ---
    stop_all_services()
    STOP_EVENT.clear()

    # --- 步驟 1: 準備原始碼 (已修復的核心邏輯) ---
    should_clone = False
    if not PROJECT_PATH.exists():
        should_clone = True
        print(f"專案目錄 {PROJECT_PATH} 不存在，準備執行 clone。")
    elif FORCE_REPO_REFRESH:
        should_clone = True
        print(f"偵測到強制刷新選項，正在刪除舊專案目錄: {PROJECT_PATH}")
        shutil.rmtree(PROJECT_PATH)
        print("舊專案目錄已移除。")
    else:
        print("✅ 專案目錄已存在且未強制刷新，跳過下載。")

    # 只有在需要時才執行 clone，並在此之後才初始化日誌系統
    if should_clone:
        # 暫時直接打印，因為日誌檔案還不存在
        print(f"🚀 開始執行: 從 GitHub 拉取後端程式碼 (分支: {TARGET_BRANCH})...")
        clone_process = subprocess.run(
            ["git", "clone", "--branch", TARGET_BRANCH, REPOSITORY_URL, str(PROJECT_PATH)],
            capture_output=True, text=True
        )
        if clone_process.returncode != 0:
            print("💥 Git Clone 失敗! 錯誤訊息:")
            print(clone_process.stderr)
            raise RuntimeError("無法從 GitHub 下載專案，請檢查 URL 和分支名稱。")
        print("✅ 成功完成: 從 GitHub 拉取後端程式碼")

    # --- 步驟 2: 初始化日誌系統 ---
    # 現在專案目錄已確定存在，可以安全地初始化日誌
    if LOG_FILE_PATH.exists(): LOG_FILE_PATH.unlink()
    LOG_TAILER_THREAD = LogTailer(LOG_FILE_PATH, STOP_EVENT)
    LOG_TAILER_THREAD.start()
    log_message("日誌監控系統已啟動。")

    # --- 步驟 3: 設定 AI 模型 ---
    config_path = PROJECT_PATH / "src" / "core" / "config.py"
    if config_path.exists():
        log_message(f"正在設定 AI 模型大小為: {MODEL_SIZE}")
        content = config_path.read_text(encoding='utf-8')
        new_content = re.sub(r"(MODEL_SIZE\s*=\s*)\"[^\"]*\"", f'\\g<1>\"{MODEL_SIZE}\"', content)
        config_path.write_text(new_content, encoding='utf-8')
        log_message(f"✅ AI 模型已設定完畢。")
    else:
        log_message(f"⚠️ 警告: 未在 {config_path} 找到設定檔，將使用專案預設模型。")

    # --- 步驟 4: 安裝依賴 ---
    # 修正：在執行依賴安裝前，先安裝 uv
    run_shell_command(
        [sys.executable, "-m", "pip", "install", "uv"],
        title="安裝 uv 依賴管理工具"
    )

    run_shell_command(
        [sys.executable, "commander_console.py", "install-deps"],
        cwd=PROJECT_PATH,
        title="使用 commander_console 安裝所有作戰依賴"
    )

    # --- 步驟 5: 啟動伺服器 ---
    start_server()

    # 增加等待時間以確保服務完全啟動
    time.sleep(20)
    if SERVER_PROCESS.poll() is not None:
        raise RuntimeError("伺服器未能成功啟動或在啟動過程中崩潰，請檢查上方日誌以了解詳細原因。")

    # --- 步驟 6: 生成公開網址並顯示 ---
    log_message("正在生成 Colab 公開代理網址...")
    proxy_url = colab_output.eval_js(f'google.colab.kernel.proxyPort({PORT})')
    log_message(f"✅ 公開網址已生成: {proxy_url}")

    clear_output(wait=True)
    display(HTML(f"""
    <div style="border: 2px solid #4CAF50; padding: 16px; margin: 15px 0; background-color: #f0fff0; border-radius: 8px;">
        <h2 style="margin-top: 0; color: #333;">✅ 作戰系統已上線！</h2>
        <p style="font-size: 1.1em;">所有安裝與啟動步驟已完成，請點擊下方連結開啟指揮中心：</p>
        <a href="{proxy_url}" target="_blank"
           style="font-size: 1.5em; font-weight: bold; color: white; background-color: #4CAF50; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
            🚀 開啟鳳凰轉錄儀指揮中心 🚀
        </a>
        <p style="font-size: 0.9em; color: #555; margin-top: 15px;">
        ⚠️ <b>要停止伺服器，請點擊 Colab 此儲存格執行按鈕左側的「中斷執行」(■) 方塊。</b><br>
        詳細的執行日誌會顯示在下方，並在任務結束後自動歸檔。
        </p>
    </div>
    """))

    print("\n" + "="*80)
    print("📜 即時作戰日誌 (日誌檔案將在停止後歸檔)")
    print("="*80 + "\n")

    while not STOP_EVENT.is_set():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            log_message("\n[偵測到使用者手動中斷請求...]")
            break

except Exception as e:
    print("\n" + "="*80)
    print(f"💥 作戰流程發生未預期的嚴重錯誤: {e}")
    print("="*80)
    try:
        log_message(f"💥 作戰流程發生未預期的嚴重錯誤: {e}")
    except:
        pass

finally:
    stop_all_services()
    archive_log_file()
    print("\n" + "="*80)
    print("✅ 部署流程已結束，所有服務已安全關閉。")
    print("="*80)
