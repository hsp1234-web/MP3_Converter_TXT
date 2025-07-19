import subprocess
import os
from google.colab import output

# --- 組態設定 ---
GIT_REPO_URL = "https://github.com/your-username/your-repo-name.git"  # 請替換成您的儲存庫 URL
# --- 組態設定結束 ---

def run_command(command):
    """執行一個 shell 指令並即時印出其輸出。"""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True, bufsize=1, encoding='utf-8')
    for line in iter(process.stdout.readline, ''):
        print(line, end='')
    process.stdout.close()
    return_code = process.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, command)

def main():
    """主要部署腳本。"""
    print("--- 開始部署 ---")

    # 步驟 1: 複製儲存庫
    print("\n--- 步驟 1: 正在複製儲存庫 ---")
    if os.path.exists("phoenix_transcriber"):
        print("儲存庫已存在，跳過複製步驟。")
    else:
        run_command(f"git clone {GIT_REPO_URL} phoenix_transcriber")
    os.chdir("phoenix_transcriber")

    # 步驟 2: 安裝 uv
    print("\n--- 步驟 2: 正在安裝 uv ---")
    run_command("curl -LsSf https://astral.sh/uv/install.sh | sh")
    os.environ["PATH"] += ":/root/.cargo/bin"


    # 步驟 3: 使用 uv 安裝依賴套件
    print("\n--- 步驟 3: 正在使用 uv 安裝依賴套件 ---")
    run_command("uv pip install -r requirements.txt")

    # 步驟 4: 啟動應用程式
    print("\n--- 步驟 4: 正在啟動應用程式 ---")
    # 我們需要在背景執行啟動器
    process = subprocess.Popen(["python", "src/launcher.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


    # 步驟 5: 將應用程式的連接埠作為服務提供
    print("\n--- 步驟 5: 正在提供應用程式連接埠 ---")
    output.serve_kernel_port_as_window(8000, anchor_text="點擊此處開啟應用程式")

    print("\n--- 部署完成 ---")
    # 保持腳本執行以維持伺服器運作
    try:
        while True:
            # 您可以在此處添加健康檢查
            line = process.stdout.readline()
            if not line:
                break
            print(line.decode('utf-8').strip())

    except KeyboardInterrupt:
        print("--- 正在關閉 ---")
        process.terminate()


if __name__ == "__main__":
    main()
