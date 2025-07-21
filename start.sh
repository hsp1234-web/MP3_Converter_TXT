#!/bin/bash

# 【磐石協議 v3.0】高可靠性啟動器
# 本腳本確保所有操作都在 Poetry 的控制下進行，
# 並將任何啟動失敗都轉化為有明確日誌的、可供分析的事件。

set -e # 任何指令失敗都會立即中止腳本

LOG_FILE="startup_full_log.txt"

echo "--- [階段 1] 清理舊日誌 ---"
rm -f $LOG_FILE

# 將所有後續的標準輸出和標準錯誤都重定向到日誌文件和控制台
exec &> >(tee -a "$LOG_FILE")

echo "--- [階段 2] 驗證並同步 Poetry 環境 ---"
# 確保使用正確的 Python 版本 (如果專案有鎖定)
# poetry env use python3.12

echo "正在安裝/同步依賴..."
poetry install --no-interaction

echo "--- [階段 3] 執行「領航員」預檢系統 ---"
echo "執行 Ruff 靜態掃描..."
poetry run ruff check .

echo "執行 Deptry 依賴檢查..."
poetry run deptry .

echo "執行 Ignition Test 導入測試..."
# 假設 ignition_test.py 存在於 tests/ 目錄
poetry run pytest tests/ignition_test.py

echo "--- [階段 4] 初始化資料庫 ---"
poetry run python initialize_db.py

echo "--- [階段 5] 啟動主服務 ---"
echo "使用 commander_console.py 啟動服務，預設 2 個工人..."
# 這是核心：所有服務啟動都必須通過 poetry run
poetry run python commander_console.py run-server --profile production --num-workers=2

echo "--- 服務已啟動 ---"
