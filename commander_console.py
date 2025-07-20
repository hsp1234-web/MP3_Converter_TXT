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
    執行完整的自動化測試套件，並自動設定正確的 PYTHONPATH。
    """
    import subprocess
    import os
    print("==> 正在設定測試環境...")
    test_env = os.environ.copy()
    # 關鍵修正：將專案根目錄加入 PYTHONPATH，讓測試能找到模組
    project_root = os.path.abspath(os.path.dirname(__file__))
    current_pythonpath = test_env.get("PYTHONPATH", "")
    test_env["PYTHONPATH"] = f".:{current_pythonpath}"

    print(f"==> PYTHONPATH 已設定為: {test_env['PYTHONPATH']}")
    print("==> 正在啟動 pytest...")
    try:
        # 使用修改後的環境變數來執行測試
        subprocess.check_call(["python", "-m", "pytest", "-v"], env=test_env)
        print("==> 所有測試皆已通過。")
    except subprocess.CalledProcessError as e:
        print(f"==> 測試失敗: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("==> 錯誤: 'pytest' 未找到。請先執行 'install-deps'。")
        sys.exit(1)

if __name__ == "__main__":
    cli()
