#!/bin/bash

# 鳳凰專案一鍵啟動腳本 (Phoenix Project One-Click Start Script)
#
# 這個腳本將在任何支援 Bash 的 Linux 環境 (包括 Ubuntu, Debian, CentOS, and Google Colab)
# 中，自動化所有必要的設定，最終提供一個可公開存取的測試網址。

# --- 設定顏色代碼以便日誌輸出 ---
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_RED='\033[0;31m'
COLOR_BOLD='\033[1m'
COLOR_RESET='\033[0m'

# --- 輔助函式 ---
print_step() {
    echo -e "\n${COLOR_BOLD}${COLOR_GREEN}--- $1 ---${COLOR_RESET}"
}

print_info() {
    echo -e "${COLOR_YELLOW}⏳ $1${COLOR_RESET}"
}

print_success() {
    echo -e "${COLOR_GREEN}✅ $1${COLOR_RESET}"
}

print_error() {
    echo -e "${COLOR_RED}❌ $1${COLOR_RESET}"
}

# --- 腳本主體 ---
main() {
    # 強制關閉可能佔用 8000 連接埠的進程
    fuser -k 8000/tcp || true

    # 當腳本被中斷或出錯時，確保所有子行程都被關閉
    trap 'cleanup_and_exit' SIGINT SIGTERM ERR

    print_step "步驟 1: 環境檢查與工具安裝"

    # 檢查 Git
    if ! command -v git &> /dev/null; then
        print_info "未找到 Git，正在嘗試安裝..."
        sudo apt-get update && sudo apt-get install -y git || { print_error "Git 安裝失敗，請手動安裝後再試。"; exit 1; }
    fi
    print_success "Git 已安裝。"

    # 檢查 Python 3
    if ! command -v python3 &> /dev/null; then
        print_info "未找到 Python 3，正在嘗試安裝..."
        sudo apt-get update && sudo apt-get install -y python3 python3-pip || { print_error "Python 3 安裝失敗，請手動安裝後再試。"; exit 1; }
    fi
    print_success "Python 3 已安裝。"

    # 檢查 psmisc (包含 fuser)
    if ! command -v fuser &> /dev/null; then
        print_info "未找到 fuser，正在嘗試安裝 psmisc..."
        sudo apt-get update && sudo apt-get install -y psmisc || { print_error "psmisc 安裝失敗，請手動安裝後再試。"; exit 1; }
        hash -r
    fi
    print_success "fuser 已安裝。"

    print_step "步驟 2: 啟動通用啟動器"

    if [ ! -f "universal_launcher.py" ]; then
        print_error "找不到 'universal_launcher.py'。請確認專案庫中包含此檔案。"
        exit 1
    fi

    # 賦予啟動器執行權限
    chmod +x universal_launcher.py

    # 執行 Python 啟動器，並將其 PID 儲存起來
    # 使用 stdbuf -oL 來確保 Python 的輸出是即時的 (line-buffered)
    stdbuf -oL python3 universal_launcher.py &
    LAUNCHER_PID=$!

    # 等待 Python 腳本結束
    wait $LAUNCHER_PID
}

cleanup_and_exit() {
    print_info "\n\n收到關閉信號，正在清理背景行程..."
    # LAUNCHER_PID 是我們在背景執行的 Python 腳本
    # Python 腳本內部已經有自己的清理機制 (會關閉 server 和 ssh)
    # 我們只需要確保 Python 腳本本身被終止即可。
    if ps -p $LAUNCHER_PID > /dev/null; then
        kill $LAUNCHER_PID
    fi
    print_success "清理完畢。腳本終止。"
    exit 0
}

# --- 執行主函式 ---
main
