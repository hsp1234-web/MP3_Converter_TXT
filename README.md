# 鳳凰專案 (Phoenix Project)

本專案是一個模組化、可擴展的錄音轉寫服務。其核心設計理念是提供一個結構清晰、易於維護、且具備自我驗證能力的系統。

## 核心原則

*   **萬能鑰匙 (`commander_console.py`)**: 所有後台任務、數據處理和服務啟動的唯一入口點。
*   **活的儀表板 (`README.md`)**: 本文件，提供清晰、可執行的系統能力清單。
*   **功能契約 (`tests/test_capabilities.py`)**: 自動化測試，確保儀表板中描述的所有能力都真實可用。

---

## 系統能力清單 (活的儀表板)

以下是可透過「萬能鑰匙」(`commander_console.py`) 執行的所有核心指令。

### 1. 安裝/更新依賴
安裝專案所需的所有 Python 依賴套件。
```bash
python commander_console.py install-deps
```

### 2. 執行自動化測試
執行完整的測試套件，以驗證系統所有功能的正確性。
```bash
python commander_console.py run-tests
```

### 3. 啟動服務 (測試模式)
以 `testing` 配置啟動 API 伺服器及背景工人。此模式使用輕量級模型，適合開發與快速驗證。
```bash
python commander_console.py run-server --profile testing
```
或者，使用預設配置：
```bash
python commander_console.py run-server
```

### 4. 啟動服務 (生產模式)
以 `production` 配置啟動服務。此模式使用更強大的模型，適用於正式部署。
```bash
python commander_console.py run-server --profile production
```

---

## 在 Google Colab 中運行

我們提供了一個專業的啟動器，讓您可以在 Google Colab 環境中輕鬆啟動本專案。

詳細的操作說明與程式碼，請參閱：

[**Google Colab 專業啟動器 (COLAB_LAUNCHER.md)**](./COLAB_LAUNCHER.md)

---

## 專案結構

- `commander_console.py`: 所有操作的統一入口。
- `pyproject.toml`: 定義專案元數據和頂層依賴。
- `uv.lock`: 鎖定所有依賴的確切版本，確保環境可重複。
- `src/`: 應用程式原始碼。
  - `src/core/__init__.py`: 核心模組，整合了設定、日誌和資料庫功能。
  - `src/main.py`: FastAPI 應用程式的進入點。
  - `src/transcriber_worker.py`: 負責執行轉寫任務的工人。
  - `src/mock_worker.py`: 用於測試的模擬工人。
- `tests/`: 自動化測試。
  - `tests/test_capabilities.py`: 「功能契約」的實現，確保本 README 中的指令有效。
