# 【功能契約測試】
# 這個測試的目的是確保 README.md 中「系統能力清單」列出的所有命令都是可執行的。
# 它將文檔變成了可執行的測試，是我們主動防禦體系的重要一環。

import re
import subprocess
import pytest
from pathlib import Path

# --- 常數定義 ---
README_FILE = Path(__file__).parent.parent / "README.md"
CAPABILITIES_HEADER = "# 【系統能力清單 (System Capabilities)】"

# --- 測試輔助函數 ---

def parse_commands_from_readme() -> list[str]:
    """
    從 README.md 中解析出「系統能力清單」區塊下的所有 shell 命令。
    """
    if not README_FILE.exists():
        pytest.fail(f"無法找到 README.md 文件於: {README_FILE}")

    content = README_FILE.read_text(encoding="utf-8")

    # 尋找能力清單區塊
    if CAPABILITIES_HEADER not in content:
        pytest.fail(f"在 README.md 中找不到 '{CAPABILITIES_HEADER}' 標題。")

    # 提取標頭之後，下一個 "---" 分隔符之前的所有內容
    try:
        capabilities_section = content.split(CAPABILITIES_HEADER)[1].split("---")[0]
    except IndexError:
        pytest.fail("無法正確解析「系統能力清單」區塊。")

    # 使用正則表達式尋找所有 ```bash ... ``` 程式碼塊中的內容
    # re.DOTALL 使得 `.` 可以匹配換行符
    command_blocks = re.findall(r"```bash\n(.*?)\n```", capabilities_section, re.DOTALL)

    # 如果上面的正則表達式找不到，嘗試一個稍微寬鬆的版本，它不要求最後一個換行符
    if not command_blocks:
        command_blocks = re.findall(r"```bash\n(.*?)```", capabilities_section, re.DOTALL)


    # 清理每個命令，去除多餘的空白
    commands = [cmd.strip() for block in command_blocks for cmd in block.split('\n') if cmd.strip()]

    if not commands:
        pytest.fail("在「系統能力清單」中沒有找到任何有效的命令。")

    return commands

# --- 測試主體 ---

# 使用 parametrize 將找到的每個命令都作為一個獨立的測試案例
@pytest.mark.parametrize("command", parse_commands_from_readme())
def test_capability_command(command: str):
    """
    驗證從 README.md 解析出的單個命令是否可以成功執行。
    """
    # 根據指揮官指示，我們跳過會遞歸調用或檢查風格的命令
    if "poetry run pytest" in command or "ruff" in command or "deptry" in command:
        pytest.skip(f"根據指示跳過契約命令測試: {command}")

    # 我們不能測試 `start.sh` 本身，因為它會啟動一個無限循環的服務。
    # 我們在這裡對其進行特殊處理，只檢查它的語法是否正確。
    if "start.sh" in command:
        command_to_run = f"bash -n {command.split()[0]}" # -n 選項會檢查語法而不執行
        expected_timeout = 5
        success_message = f"命令 '{command}' 的語法正確。"
        failure_message = f"命令 '{command}' 存在語法錯誤。"
    else:
        command_to_run = command
        expected_timeout = 60  # 給其他命令更長的超時時間
        success_message = f"命令 '{command}' 成功執行。"
        failure_message = f"命令 '{command}' 執行失敗。"

    try:
        print(f"\n--> 正在測試契約命令: [{command_to_run}]")
        # 使用 subprocess.run 執行命令
        result = subprocess.run(
            command_to_run,
            shell=True,
            check=True,        # 如果返回非零退出碼，則引發 CalledProcessError
            capture_output=True, # 捕獲 stdout 和 stderr
            text=True,         # 以文本模式處理輸出
            timeout=expected_timeout # 設定超時
        )
        print(success_message)
        # 可選：打印輸出以供調試
        # print(f"STDOUT:\n{result.stdout}")
        # print(f"STDERR:\n{result.stderr}")

    except subprocess.CalledProcessError as e:
        pytest.fail(
            f"{failure_message}\n"
            f"返回碼: {e.returncode}\n"
            f"STDOUT:\n{e.stdout}\n"
            f"STDERR:\n{e.stderr}"
        )
    except subprocess.TimeoutExpired as e:
        pytest.fail(
            f"命令 '{command}' 執行超時 ({expected_timeout}秒)。\n"
            f"STDOUT:\n{e.stdout}\n"
            f"STDERR:\n{e.stderr}"
        )
    except FileNotFoundError:
        pytest.fail(f"命令 '{command}' 中的程式未找到。請檢查環境和 PATH。")
    except Exception as e:
        pytest.fail(f"執行命令 '{command}' 時發生未知錯誤: {e}")
