#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
鳳凰專案通用啟動器 (Phoenix Project Universal Launcher)

本腳本旨在任何 Ubuntu 環境（包括本地端與 Google Colab）中，
提供一個單一指令即可完成所有設定、啟動服務並取得公開網址的解決方案。

特色：
- 自動化：包辦所有流程，從安裝依賴到生成網址。
- 穩健性：包含日誌監控、錯誤處理與重試機制。
- 通用性：無需修改即可在不同 Ubuntu 環境中運行。
"""

import os
import sys
import time
import subprocess
import threading
from pathlib import Path
import re

# --- 全域設定 ---
PROFILE = "testing"  # 可在此修改為 "production"
SERVER_PORT = 8000
MAX_SSH_RETRIES = 3
SSH_RETRY_DELAY = 5 # seconds

# --- 路徑設定 (由 start.sh 確保當前工作目錄為專案根目錄) ---
PROJECT_PATH = Path.cwd()

COMMANDER_CONSOLE_PATH = PROJECT_PATH / "commander_console.py"
LOG_FILE_PATH = PROJECT_PATH / "phoenix_transcriber.log"
PYTHON_EXECUTABLE = sys.executable

# --- 顏色代碼 ---
class Color:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

# --- 輔助函式 ---
def print_step(message):
    print(f"\n{Color.BOLD}{Color.GREEN}--- {message} ---{Color.END}")

def print_info(message):
    print(f"{Color.YELLOW}⏳ {message}{Color.END}")

def print_success(message):
    print(f"{Color.GREEN}✅ {message}{Color.END}")

def print_error(message):
    print(f"{Color.RED}❌ {message}{Color.END}")

def run_command(command, cwd, description):
    """執行一個命令，並在失敗時拋出例外。"""
    print_info(f"正在執行: {description}")
    process = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding='utf-8')
    if process.returncode != 0:
        print_error(f"{description} 失敗。")
        print(f"--- STDOUT ---\n{process.stdout}")
        print(f"--- STDERR ---\n{process.stderr}")
        raise subprocess.CalledProcessError(process.returncode, command, output=process.stdout, stderr=process.stderr)
    print_success(f"{description} 完成。")
    return process

# --- 核心流程 ---
def start_server():
    """在背景啟動鳳凰專案伺服器。"""
    print_step("步驟 2: 啟動鳳凰專案伺服器")
    log_file_handle = open(LOG_FILE_PATH, 'w')
    process = subprocess.Popen(
        [PYTHON_EXECUTABLE, str(COMMANDER_CONSOLE_PATH), "run-server", "--profile", PROFILE],
        cwd=PROJECT_PATH,
        stdout=log_file_handle,
        stderr=subprocess.STDOUT
    )
    print_info(f"伺服器正在背景啟動，日誌將寫入: {LOG_FILE_PATH}")
    return process, log_file_handle

def monitor_server_log(timeout=60):
    """監控日誌檔案，確認 Uvicorn 是否成功啟動。"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if LOG_FILE_PATH.exists():
            with open(LOG_FILE_PATH, 'r') as f:
                for line in f:
                    if "Uvicorn running on" in line:
                        print_success("偵測到 Uvicorn 伺服器成功運行！")
                        return True
                    if "ERROR" in line.upper() or "Traceback" in line:
                        print_error(f"伺服器啟動失敗，請檢查日誌: {LOG_FILE_PATH}")
                        return False
        time.sleep(1)
    print_error("等待伺服器啟動超時。")
    return False

def start_ssh_tunnel(port):
    """啟動 localhost.run SSH 通道，並包含重試機制。"""
    print_step("步驟 3: 建立臨時公開網址 (使用 localhost.run)")
    command = [
        "ssh",
        "-R", f"80:localhost:{port}",
        "-o", "StrictHostKeyChecking=no", # 避免主機金鑰檢查提示
        "-o", "UserKnownHostsFile=/dev/null", # 不儲存主機金鑰
        "-o", "ServerAliveInterval=60", # 保持連線
        "ssh.localhost.run"
    ]

    for attempt in range(MAX_SSH_RETRIES):
        print_info(f"正在嘗試建立 SSH 通道 (第 {attempt + 1}/{MAX_SSH_RETRIES} 次)...")
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')

        # 使用線程來處理 stdout，避免阻塞
        output_holder = {"url": None, "error": None}
        def read_pipe(pipe, key):
            try:
                for line in iter(pipe.readline, ''):
                    print(f"   [SSH] {line.strip()}")
                    # 尋找 HTTPS 網址
                    match = re.search(r'(https?://\S+)', line)
                    if match:
                        output_holder["url"] = match.group(1)
                        break
            except Exception as e:
                output_holder["error"] = str(e)

        stdout_thread = threading.Thread(target=read_pipe, args=(process.stdout, "url"))
        stderr_thread = threading.Thread(target=read_pipe, args=(process.stderr, "url"))
        stdout_thread.start()
        stderr_thread.start()

        # 等待最多 20 秒來獲取網址
        stdout_thread.join(timeout=20)
        stderr_thread.join(timeout=5)

        if output_holder["url"]:
            print_success(f"成功獲取公開網址！")
            return process, output_holder["url"]

        print_error("無法從 localhost.run 的輸出中找到網址。")
        process.terminate()
        if attempt < MAX_SSH_RETRIES - 1:
            print_info(f"將在 {SSH_RETRY_DELAY} 秒後重試...")
            time.sleep(SSH_RETRY_DELAY)
        else:
            print_error("已達最大重試次數，建立通道失敗。")
            return None, None

def main():
    """主執行函數"""
    server_process = None
    log_handle = None
    ssh_process = None

    try:
        print_step("步驟 1: 安裝專案依賴")
        run_command([PYTHON_EXECUTABLE, str(COMMANDER_CONSOLE_PATH), "install-deps"], PROJECT_PATH, "安裝依賴套件")

        server_process, log_handle = start_server()

        if not monitor_server_log():
            raise RuntimeError("伺服器未能成功啟動。")

        ssh_process, public_url = start_ssh_tunnel(SERVER_PORT)

        if not public_url:
            raise RuntimeError("未能成功建立 SSH 通道。")

        print("\n" + "="*50)
        print(f"{Color.BOLD}🎉 鳳凰專案已成功啟動！ 🎉{Color.END}")
        print(f"您可以透過以下公開網址存取服務：")
        print(f"{Color.GREEN}{Color.BOLD}👉 {public_url} 👈{Color.END}")
        print("="*50)
        print("\n(本腳本會持續運行以保持服務開啟，按 Ctrl+C 即可關閉所有服務)")

        # 等待，直到使用者中斷
        while True:
            time.sleep(1)

    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 收到使用者中斷信號，正在優雅地關閉所有服務...")
    except Exception as e:
        print_error(f"啟動過程中發生未預期的錯誤: {e}")
    finally:
        if ssh_process and ssh_process.poll() is None:
            print_info("正在關閉 SSH 通道...")
            ssh_process.terminate()
        if server_process and server_process.poll() is None:
            print_info("正在關閉鳳凰專案伺服器...")
            server_process.terminate()
        if log_handle:
            log_handle.close()
        print_success("所有服務已成功關閉。再會！")

if __name__ == "__main__":
    main()
