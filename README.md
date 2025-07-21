# 鳳凰專案 (Phoenix Project)

本專案是一個模組化、可擴展的錄音轉寫服務。其核心設計理念是提供一個結構清晰、易於維護、且具備自我驗證能力的系統。

---

## 🚀 快速啟動選項

我們提供多種啟動方式，您可以根據您的環境和需求選擇最適合的一種。

### 1. 在 Google Colab 中啟動 (推薦給所有使用者)

這是最簡單、最快速的方式，不需在您自己的電腦上安裝任何東西。

[![在 Colab 中開啟](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/hsp1234-web/MP3_Converter_TXT/blob/main/colab_deployment_script.py)

**點擊上方按鈕**，即可在 Google Colab 中打開我們的部署腳本。接著，點擊頁面上的「執行」按鈕，稍待幾分鐘，您就能獲得一個公開的服務網址，可以直接開始使用。

想了解更多細節？請參考我們的 [**Colab 使用教學**](./COLAB_USAGE.md)。

### 2. 本地一鍵啟動 (適合開發者)

如果您是開發者，且希望在自己的 Linux 環境中啟動服務，可以使用我們提供的一鍵啟動腳本。

```bash
curl -sSL https://raw.githubusercontent.com/hsp1234-web/MP3_Converter_TXT/main/start.sh | bash
```

這個指令會自動處理環境檢查、專案下載、依賴安裝、並啟動所有服務。

---

## 🛠️ 手動操作 (進階開發者模式)

如果您想深入了解或控制每一個步驟，可以依照以下方式手動操作。

### 1. 下載專案
```bash
git clone https://github.com/hsp1234-web/MP3_Converter_TXT.git
cd MP3_Converter_TXT
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

## 📂 專案核心檔案

- `colab_deployment_script.py`: **Colab 部署腳本**，在 Google Colab 環境中一鍵啟動服務的核心。
- `COLAB_USAGE.md`: **Colab 使用教學**，詳細解釋如何在 Colab 中使用本專案。
- `start.sh`: **本地一鍵啟動腳本**，封裝了所有操作，是開發者在本地環境快速啟動的首選。
- `universal_launcher.py`: **通用啟動器**，被 `start.sh` 所呼叫，負責處理 Python 層面的啟動邏輯。
- `commander_console.py`: **萬能鑰匙**，所有底層操作的統一入口，供進階開發者使用。
- `pyproject.toml`: 定義專案元數據和頂層依賴。
- `src/`: 應用程式原始碼。
- `tests/`: 自動化測試。

---

## 📋 系統能力清單 (System Capabilities)
<!--
此處的命令是本系統對外的「功能契約」。
`tests/test_capabilities.py` 會自動驗證此處的所有命令是否有效。
修改或新增命令時，請確保同步更新測試。
-->

- **啟動完整服務 (生產模式)**:
  ```bash
  ./start.sh
  ```

- **執行所有測試**:
  ```bash
  poetry run pytest
  ```

- **執行 Ruff 靜態掃描**:
  ```bash
  poetry run ruff check .
  ```

- **檢查依賴一致性**:
  ```bash
  poetry run deptry .
  ```
