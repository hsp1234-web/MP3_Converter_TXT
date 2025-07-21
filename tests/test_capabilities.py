"""能力測試."""
from __future__ import annotations

import subprocess
import sys

import pytest


def run_command_for_capability_test(
    command: list[str],
) -> subprocess.CompletedProcess:
    """
    為能力測試專門設計的命令執行器.

    它會執行一個命令並驗證其返回碼是否為 0.
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,  # 設定一個較短的超時
            check=True,  # 如果返回碼非 0, 將會拋出 CalledProcessError
            encoding="utf-8",
        )
        return result
    except FileNotFoundError:
        pytest.fail(f"命令 '{command[0]}' 未找到. 請確保它在系統路徑中.")
    except subprocess.CalledProcessError as e:
        pytest.fail(
            f"命令 '{' '.join(command)}' 執行失敗.\n"
            f"返回碼: {e.returncode}\n"
            f"標準輸出:\n{e.stdout}\n"
            f"標準錯誤:\n{e.stderr}",
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"命令 '{' '.join(command)}' 執行超時.")


def test_capability_install_deps_help() -> None:
    """【功能契約】驗證 `install-deps` 指令是否可用."""
    command = [sys.executable, "commander_console.py", "install-deps", "--help"]
    result = run_command_for_capability_test(command)
    assert "安裝或更新專案所需的所有 Python 依賴套件" in result.stdout


def test_capability_run_tests_help() -> None:
    """【功能契約】驗證 `run-tests` 指令是否可用."""
    command = [sys.executable, "commander_console.py", "run-tests", "--help"]
    result = run_command_for_capability_test(command)
    assert "執行完整的自動化測試套件" in result.stdout


def test_capability_run_server_help() -> None:
    """【功能契約】驗證 `run-server` 指令是否可用."""
    command = [sys.executable, "commander_console.py", "run-server", "--help"]
    result = run_command_for_capability_test(command)
    assert "啟動 API 伺服器以及對應的背景工人行程" in result.stdout
