# 鳳凰專案 (Phoenix Project)

本專案是一個模組化、可擴展的錄音轉寫服務。其核心設計理念是提供一個結構清晰、易於維護、且具備自我驗證能力的系統。

## 核心原則

*   **統一入口 (`commander_console.py`)**: 所有後台任務、數據處理和服務啟動的唯一入口點。
*   **活的儀表板 (`README.md`)**: 本文件，提供清晰、可執行的系統能力清單。
*   **功能契約 (`tests/`)**: 自動化測試，確保儀表板中描述的所有能力都真實可用。

---

## 系統能力清單 (活的儀表板)

以下是可透過「萬能鑰匙」(`commander_console.py`) 執行的所有核心指令。

### 1. 安裝/更新依賴
安裝專案所需的所有 Python 依賴套件。
```bash
poetry install
```

### 2. 執行自動化測試
執行完整的測試套件（不包括 E2E 測試）。
```bash
python commander_console.py run-tests -m "not e2e"
```

執行 E2E 測試。
```bash
python commander_console.py run-tests -m "e2e"
```

### 3. 啟動服務
以 `testing` 配置啟動 API 伺服器。
```bash
python commander_console.py run-server --profile testing
```

以 `production` 配置啟動服務。
```bash
python commander_console.py run-server --profile production
```

### 4. 資料庫管理
初始化資料庫。
```bash
python commander_console.py db-init
```

### 5. 清理專案
清理專案中的快取檔案。
```bash
python commander_console.py clean
```

---

## 專案結構

- `commander_console.py`: 所有操作的統一入口。
- `pyproject.toml`: 定義專案元數據和頂層依賴。
- `poetry.lock`: 鎖定所有依賴的確切版本，確保環境可重複。
- `src/`: 應用程式原始碼。
  - `config.py`: 定義不同環境的設定。
  - `database.py`: 處理資料庫的初始化和操作。
  - `logging_config.py`: 設定日誌系統。
  - `main.py`: FastAPI 應用程式的進入點。
  - `model_loader.py`: 負責載入 `faster-whisper` 模型。
  - `transcriber_worker.py`: 負責執行轉寫任務的工人。
  - `utils/`: 工具模組。
    - `hardware.py`: 偵測硬體並返回最佳設定。
- `tests/`: 自動化測試。
  - `e2e/`: 端對端測試。
  - `test_capabilities.py`: 「功能契約」的實現，確保本 README 中的指令有效。
