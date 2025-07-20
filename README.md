# 鳳凰專案 (Phoenix Project)

本專案是一個模組化、可擴展的錄音轉寫服務。其核心設計理念是提供一個結構清晰、易於維護、且具備自我驗證能力的系統。

---

## 🚀 一鍵啟動 (推薦)

我們提供了一個 `start.sh` 腳本，它能在任何支援 Bash 的 Linux 環境（包括 Ubuntu, Debian, CentOS, and Google Colab）中，一鍵完成所有設定並啟動服務。

### 如何使用？

只需要在您的終端機中執行以下單行指令即可：

```bash
curl -sSL https://raw.githubusercontent.com/your-username/your-repo-name/main/start.sh | bash
```
**請記得替換 `your-username` 和 `your-repo-name` 為您自己的 GitHub 使用者名稱和專案庫名稱。**

這個指令會：
1.  下載 `start.sh` 腳本。
2.  透過 `bash` 直接執行它。
3.  腳本會自動處理環境檢查、專案下載、依賴安裝、服務啟動及網址生成的所有細節。

執行完畢後，您將會直接在終端機中看到一個可公開存取的服務網址。

---

## 手動操作 (開發者模式)

如果您想深入了解或控制每一個步驟，可以依照以下方式手動操作。

### 1. 下載專案
```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

### 2. 執行通用啟動器
我們提供了一個 Python 腳本 `universal_launcher.py` 來處理所有啟動細節。
```bash
chmod +x universal_launcher.py
./universal_launcher.py
```

### 3. (可選) 更細緻的手動控制
如果您連 `universal_launcher.py` 都不想使用，可以參考 `commander_console.py` 來執行更底層的操作。
```bash
# 安裝依賴
python3 commander_console.py install-deps

# 執行測試
python3 commander_console.py run-tests

# 啟動伺服器
python3 commander_console.py run-server --profile testing
```

---

## 專案核心檔案

- `start.sh`: **一鍵啟動腳本**，封裝了所有操作，是使用者入門的首選。
- `universal_launcher.py`: **通用啟動器**，被 `start.sh` 所呼叫，負責處理 Python 層面的啟動邏輯。
- `commander_console.py`: **萬能鑰匙**，所有底層操作的統一入口，供開發者使用。
- `pyproject.toml`: 定義專案元數據和頂層依賴。
- `src/`: 應用程式原始碼。
- `tests/`: 自動化測試。
