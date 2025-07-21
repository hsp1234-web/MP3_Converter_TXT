#!/bin/bash

# 【作戰計畫 041】最終啟動器 - 哨兵
# 職責：確保依賴同步，並以標準、可靠的方式啟動 Uvicorn 主進程。
# 靜默失敗在此終結。

set -e # 任何指令失敗都會立即中止腳本

echo "--- [哨兵] 階段 1: 同步依賴 ---"
poetry install --no-interaction

echo "--- [哨兵] 階段 2: 移交指揮權 ---"
echo "正在啟動 Uvicorn 指揮官..."
# --reload 選項已在驗證階段被暫時移除，以避免無限重啟循環
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000
