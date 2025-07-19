import pytest
import subprocess
import sys
import time
import httpx
import os

# --- 常數 ---
HEALTH_CHECK_URL = "http://localhost:8000/health"
MAX_HEALTH_RETRIES = 10
RETRY_INTERVAL = 2

# --- 輔助函式 ---
def run_command(command: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """執行一個控制台命令並回傳結果。"""
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout)

def start_server_process(profile: str) -> subprocess.Popen:
    """在背景啟動伺服器行程。"""
    command = [sys.executable, "commander_console.py", "run-server", f"--profile={profile}"]
    # 使用 Popen 在背景執行，並將輸出導向日誌檔案以便除錯
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return process

def check_server_health() -> bool:
    """檢查伺服器健康狀態端點。"""
    for i in range(MAX_HEALTH_RETRIES):
        try:
            response = httpx.get(HEALTH_CHECK_URL, timeout=1.0)
            if response.status_code == 200:
                print(f"健康探針成功！ (嘗試 {i+1}/{MAX_HEALTH_RETRIES})")
                return True
        except httpx.ConnectError:
            print(f"API 尚未就緒，等待 {RETRY_INTERVAL} 秒...")
            time.sleep(RETRY_INTERVAL)
    return False

# --- 能力測試 ---

def test_capability_install_deps():
    """驗證 'install-deps' 命令是否能成功執行。"""
    result = run_command([sys.executable, "commander_console.py", "install-deps"])
    assert result.returncode == 0
    assert "依賴套件安裝成功" in result.stdout

def test_capability_run_tests():
    """驗證 'run-tests' 命令是否能成功執行並通過所有測試（忽略能力測試本身）。"""
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--ignore=tests/test_capabilities.py"
    ]
    # 我們在這裡直接呼叫 pytest，而不是透過 commander_console，以避免遞迴
    result = run_command(command)
    assert result.returncode == 0, f"pytest 執行失敗: {result.stderr}"
    assert "failed" not in result.stdout.lower()

@pytest.mark.long_running
def test_capability_run_server_testing_profile():
    """
    驗證 'run-server --profile=testing' 命令。
    1. 啟動伺服器。
    2. 透過健康探針確認其在線。
    3. 終止伺服器。
    """
    server_process = None
    try:
        print("\n正在啟動伺服器 (profile=testing)...")
        server_process = start_server_process("testing")

        is_healthy = check_server_health()
        assert is_healthy, "伺服器健康探針失敗，無法在指定時間內啟動。"

        print("伺服器已成功啟動並通過健康檢查。")

    finally:
        if server_process:
            print("正在終止伺服器行程...")
            server_process.terminate()
            try:
                # 等待行程結束並獲取輸出
                stdout, stderr = server_process.communicate(timeout=10)
                print("伺服器輸出:\n", stdout)
                if stderr:
                    print("伺服器錯誤輸出:\n", stderr)
            except subprocess.TimeoutExpired:
                print("伺服器未能及時終止，將強制關閉。")
                server_process.kill()
