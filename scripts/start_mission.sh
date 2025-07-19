#!/bin/bash

# ==============================================================================
# 【作戰腳本】start_mission_internal_proxy.sh (內部代理版 v4)
# 作戰目標：
#   移除所有對外部通道服務 (localtunnel) 的依賴，改為完全依賴
#   平台內建的代理服務，以達成最高的作戰穩定性。
# ==============================================================================

# --- 哨兵模式與環境整備 ---
set -ex
echo "==> [階段 1/5] 準備作戰環境與日誌系統..."
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
rm -f "$LOG_DIR"/*.log
rm -f report.html
echo "==> 環境清理完畢。"
echo

# --- 依賴安裝與自動化測試 ---
echo "==> [階段 2/5] 安裝專案依賴套件..."
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install pytest-html
echo "==> [階段 3/5] 執行全系統自動化測試..."
pytest --html=report.html
echo "==> 自動化測試成功。"
echo

# --- 啟動核心服務與健康探針 ---
echo "==> [階段 4/5] 於背景啟動核心服務..."
python src/launcher.py > "$LOG_DIR/launcher.log" 2>&1 &
LAUNCHER_PID=$!
echo "==> 核心服務已嘗試啟動，PID: $LAUNCHER_PID, 日誌: $LOG_DIR/launcher.log"
echo
echo "==> [階段 5/5] 執行健康探針..."
HEALTH_CHECK_URL="http://localhost:8000/health"
MAX_HEALTH_RETRIES=10
RETRY_INTERVAL=2
PROBE_SUCCESS=false
for i in $(seq 1 $MAX_HEALTH_RETRIES); do
    if curl -sS --fail "$HEALTH_CHECK_URL"; then
        echo "==> 健康探針成功！API 服務已確認在線。"
        PROBE_SUCCESS=true
        break
    fi
    echo " - API 尚未就緒，等待 $RETRY_INTERVAL 秒 (嘗試 $i/$MAX_HEALTH_RETRIES)..."
    sleep $RETRY_INTERVAL
done

if [ "$PROBE_SUCCESS" = false ]; then
    echo "🔴 [作戰失敗] API 服務健康探針失敗。請檢查 $LOG_DIR/launcher.log"
    cat "$LOG_DIR/launcher.log"
    kill "$LAUNCHER_PID"
    exit 1
fi
echo

# --- 最終成果回報 ---
echo
echo "======================================================================"
echo "✅ 【作戰成功】系統已通過所有檢測並成功啟動！"
echo
echo "📋 視覺化作戰日誌 (本地檔案):"
echo " - file://$(pwd)/report.html"
echo
echo "🚀 服務已在本地端口 8000 上運行。"
echo "平台將自動代理並提供訪問網址。"
echo
echo "🛑 如需停止所有服務，請執行 'kill $LAUNCHER_PID' 或關閉此終端機。"
echo "======================================================================"
