import logging
import os
import subprocess
import sys
import click

# --- 主命令群組 ---
@click.group()
def cli():
    """
    鳳凰錄音轉寫服務 - 離線任務控制台。
    此控制台用於執行一次性的維護、安裝和測試任務。
    服務啟動請直接使用 start.sh。
    """
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')

@cli.command(name="install-deps")
def install_deps():
    """
    使用 Poetry 安裝或更新專案所需的所有 Python 依賴套件。
    """
    click.echo("==> 正在使用 Poetry 安裝/同步依賴套件...")
    try:
        subprocess.check_call(["poetry", "install", "--no-interaction"])
        click.secho("==> 依賴套件安裝成功。", fg="green")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        click.secho(f"==> 依賴套件安裝失敗: {e}", fg="red")
        sys.exit(1)


@cli.command(name="run-tests")
def run_tests():
    """
    使用 Poetry 執行完整的自動化測試套件。
    """
    click.echo("==> 正在啟動 pytest...")
    try:
        # 確保 src 在 PYTHONPATH 中，以便 pytest 能找到模組
        env = os.environ.copy()
        env["PYTHONPATH"] = "."
        subprocess.check_call(["poetry", "run", "pytest", "-v"], env=env)
        click.secho("==> 所有測試皆已通過。", fg="green")
    except subprocess.CalledProcessError:
        click.secho("==> 部分或全部測試失敗。", fg="red")
        sys.exit(1)
    except FileNotFoundError:
        click.secho("==> 錯誤: 'poetry' 未找到或專案未初始化。", fg="red")
        sys.exit(1)

if __name__ == "__main__":
    cli()
