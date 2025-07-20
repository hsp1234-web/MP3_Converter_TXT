#!/bin/bash

# 安裝 psmisc (包含 fuser)
if ! command -v fuser &> /dev/null
then
    echo "fuser command not found, installing psmisc..."
    export DEBIAN_FRONTEND=noninteractive
    sudo apt-get update && sudo apt-get install -y psmisc
    # 更新 shell 的 PATH
    hash -r
fi

# 強制關閉任何可能佔用 8000 連接埠的進程
fuser -k 8000/tcp

# 啟動 FastAPI 應用程式，並將日誌輸出到 uvicorn.log
nohup poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --log-level debug > uvicorn.log 2>&1 &
