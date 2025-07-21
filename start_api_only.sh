#!/bin/bash

# 【手術刀模式】API 伺服器獨立啟動器
# 這個腳本只用於偵錯，它會獨立啟動 FastAPI/Uvicorn 伺服器，
# 不涉及 commander_console 或任何多進程管理，以便我們能觀察到純淨的錯誤輸出。

echo "--- [手術刀模式] 正在獨立啟動 API 伺服器 ---"
echo "日誌將直接輸出到此控制台。"

# 確保所有操作都在 Poetry 的控制下進行
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
