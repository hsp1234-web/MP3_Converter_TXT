#!/bin/bash

# 預設工人數量
NUM_WORKERS=2

# 啟動應用程式
python commander_console.py run-server --profile production --num-workers $NUM_WORKERS
