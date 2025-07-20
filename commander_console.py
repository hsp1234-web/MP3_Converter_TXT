# commander_console.py

import sys
from pathlib import Path
import typer
import uvicorn

# --- 根本性修復 ---
# 取得此檔案所在的目錄，並將其加入到 Python 的模組搜尋路徑中。
# 這能確保無論從何處執行此腳本，Python 都能找到 'src' 這個模組。
# 這是解決方案的核心。
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))
# --- 修復結束 ---

# 初始化 Typer 命令列應用
cli = typer.Typer()

@cli.command()
def run_server(host: str = "127.0.0.1", port: int = 8000):
    """
    啟動 FastAPI 應用程式伺服器。
    """
    print(f"INFO:     啟動伺服器於 http://{host}:{port}")
    uvicorn.run("src.main:app", host=host, port=port, reload=True)

@cli.command()
def run_tests():
    """
    執行單元和整合測試（排除 E2E 測試）。
    """
    import subprocess
    import os
    print("==> 正在執行單元/整合測試...")
    test_env = os.environ.copy()
    test_env["PYTHONPATH"] = str(ROOT_DIR)

    command = ["python", "-m", "pytest", "-v", "--ignore=e2e"]

    try:
        subprocess.check_call(command, env=test_env)
        print("✅ 單元/整合測試通過。")
    except subprocess.CalledProcessError as e:
        print(f"❌ 單元/整合測試失敗: {e}")
        sys.exit(1)

@cli.command()
def run_e2e_tests():
    """
    獨立執行端對端（E2E）測試。
    """
    import subprocess
    import os
    print("==> 正在執行 E2E 測試...")
    test_env = os.environ.copy()
    test_env["PYTHONPATH"] = str(ROOT_DIR)

    command = ["python", "-m", "pytest", "-v", "e2e/"]

    try:
        subprocess.check_call(command, env=test_env)
        print("✅ E2E 測試通過。")
    except subprocess.CalledProcessError as e:
        print(f"❌ E2E 測試失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    cli()
