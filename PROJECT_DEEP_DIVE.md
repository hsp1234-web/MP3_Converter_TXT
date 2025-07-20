# 專案深度剖析 (Project Deep Dive)

本文檔旨在深入剖析「鳳凰專案」的每一個角落，提供比 `README.md` 更詳盡的技術細節、檔案職責、以及潛在的技術債分析。

---

## `src` 原始碼目錄分析

### `config.py`

*   **職責**: 管理專案的所有設定。
*   **主要功能**:
    *   定義了 `testing` 和 `production` 兩種設定檔 (Profile)。
    *   使用 `pydantic` 來建立強型別的設定類別，確保設定的正確性。
    *   提供 `get_config` 函式，可以根據傳入的 profile 名稱來取得對應的設定物件。
*   **使用技術**: `pydantic`

### `database.py`

*   **職責**: 處理資料庫的初始化和結構定義。
*   **主要功能**:
    *   定義了 `transcription_tasks` 資料表的結構，用來儲存轉寫任務的狀態。
    *   使用 `sqlite3` 作為資料庫引擎。
    *   建立了一個觸發器 (Trigger)，可以在更新任務時自動更新 `updated_at` 時間戳。
*   **使用技術**: `sqlite3`

### `logging_config.py`

*   **職責**: 設定全域的日誌系統。
*   **主要功能**:
    *   提供 `get_logger` 函式，可以取得一個設定好的 logger 實例。
    *   為了在多行程環境下安全地寫入日誌，它使用 `multiprocessing.Queue` 來建立一個中央的日誌佇列。
    *   有一個 `log_writer_process` 函式，它會在一個獨立的行程中執行，專門負責從佇列中讀取日誌並寫入檔案。
*   **使用技術**: `logging`, `multiprocessing`

### `main.py`

*   **職責**: FastAPI 應用程式的進入點，負責處理 HTTP 請求。
*   **主要功能**:
    *   定義了 FastAPI 應用程式的生命週期 (`lifespan`)，在伺服器啟動時會非同步地載入 `faster-whisper` 模型。
    *   提供了三個 API 端點 (Endpoints):
        *   `GET /`: 提供前端的 `index.html`。
        *   `GET /api/status`: 回傳目前模型的狀態 (例如：載入中、準備就緒)。
        *   `POST /api/transcribe`: 接收使用者上傳的音訊檔案，並將轉寫任務加入到背景任務中。
    *   使用 `StaticFiles` 來提供靜態檔案 (CSS)。
*   **使用技術**: `fastapi`

### `mock_worker.py`

*   **職責**: 一個模擬的工人行程，主要用於測試目的。
*   **主要功能**:
    *   模擬從任務佇列中接收任務，並在短暫延遲後回傳一個假的轉寫結果。
    *   這使得在測試時不需要真的載入龐大的 `faster-whisper` 模型，可以加速測試流程。
*   **使用技術**: `multiprocessing`

### `model_loader.py`

*   **職責**: 專門負責載入 `faster-whisper` 模型。
*   **主要功能**:
    *   呼叫 `get_best_hardware_config` 來取得最佳的硬體設定 (CUDA 或 CPU)。
    *   根據設定檔中的模型大小 (`tiny`, `medium` 等) 來載入對應的模型。
*   **使用技術**: `faster-whisper`

### `model_state.py`

*   **職責**: 管理模型的全域狀態。
*   **主要功能**:
    *   定義了一個 `ModelStatus` 的 `Enum`，包含了模型所有可能的狀態。
    *   使用全域變數 `model_instance` 和 `current_status` 來儲存模型的實例和當前狀態，讓 FastAPI 的不同部分可以共享這些資訊。

### `queues.py`

*   **職責**: 建立並提供可在多行程之間共享的佇列。
*   **主要功能**:
    *   使用 `multiprocessing.Manager` 來建立 `task_queue` 和 `result_queue`。
    *   `task_queue` 用於將轉寫任務從主行程傳遞給工人行程。
    *   `result_queue` 用於將轉寫結果從工人行程傳回主行程。
*   **使用技術**: `multiprocessing`

### `transcriber_worker.py`

*   **職責**: 真正的轉寫工人行程。
*   **主要功能**:
    *   `process_audio_file` 函式：當 API 收到檔案時，此函式會被呼叫，負責將檔案儲存到硬碟，並在資料庫中建立一筆新的任務紀錄。
    *   `transcriber_worker_process` 函式：這是一個獨立的行程，它會不斷地從 `task_queue` 中取得任務，呼叫 `faster-whisper` 模型進行轉寫，最後將結果更新回資料庫。
*   **使用技術**: `faster-whisper`, `sqlite3`

### `utils/hardware.py`

*   **職責**: 偵測硬體並回傳最佳設定。
*   **主要功能**:
    *   檢查 `torch` 是否安裝，以及 CUDA 或 Apple Silicon (MPS) 是否可用。
    *   根據偵測結果，回傳 `faster-whisper` 所需的 `device` 和 `compute_type` 設定。
*   **使用技術**: `torch` (optional)

---

## `tests` 測試目錄分析

### `conftest.py`

*   **職責**: 提供 Pytest 的 Fixtures，也就是測試用的「固定裝置」或「輔助函式」。
*   **主要功能**:
    *   定義了 `live_api_server` fixture，它會在執行 E2E (端對端) 測試前，在背景啟動一個真實的 FastAPI 伺服器。
    *   它會處理好啟動伺服器、等待伺服器準備就緒、以及在所有測試結束後關閉伺服器的所有細節。
    *   **關鍵修正**: 它手動設定了 `PYTHONPATH` 環境變數，以確保在子行程中執行的 `uvicorn` 能夠找到 `src` 目錄下的模組。
*   **使用技術**: `pytest`, `requests`, `subprocess`

### `e2e/test_api.py`

*   **職責**: 執行一個非常基本的 E2E 測試。
*   **主要功能**:
    *   使用 `live_api_server` fixture 來確保伺服器正在執行。
    *   對伺服器的根目錄 `/` 發出一個請求，並驗證是否回傳 `200 OK`。
    *   這個測試的主要目的是驗證測試環境和伺服器啟動流程是否正常。
*   **使用技術**: `pytest`, `requests`

### `test_capabilities.py`

*   **職責**: 實現「功能契約」，確保 `commander_console.py` 中的指令是可用的。
*   **主要功能**:
    *   直接透過 `subprocess` 呼叫 `commander_console.py` 的指令 (例如：`run-tests --help`)。
    *   驗證指令的輸出是否包含了預期的文字，以確保指令的功能符合 `README.md` 中的描述。
*   **使用技術**: `pytest`, `subprocess`

### `test_full_system_flow.py`

*   **職責**: 執行一個完整的系統流程測試 (E2E)。
*   **主要功能**:
    *   模擬使用者的完整操作流程：
        1.  上傳一個音訊檔案到 `/api/transcribe`。
        2.  取得回傳的 `task_id`。
        3.  使用 `task_id` 不斷地輪詢 `/api/status/{task_id}` 來查詢任務狀態。
        4.  一直等到任務狀態變成 `completed` 或 `failed`。
        5.  驗證最終的轉寫結果是否符合預期。
*   **使用技術**: `pytest`, `httpx`

### `test_server_startup.py`

*   **職責**: 測試伺服器是否能成功啟動。
*   **主要功能**:
    *   與 `e2e/test_api.py` 類似，但它呼叫的是 `/health` 端點。
    *   這是一個更明確的健康檢查。

### `test_simple.py`

*   **職責**: 一個最基本的健全性檢查 (Sanity Check)。
*   **主要功能**:
    *   執行 `assert 1 + 1 == 2`。
    *   這個測試的目的是確保 Pytest 本身可以正常運作。

### `test_worker.py`

*   **職責**: 對轉寫工人的核心邏輯進行單元測試。
*   **主要功能**:
    *   直接呼叫 `process_single_task` 函式。
    *   在測試前，手動在資料庫中插入一筆待處理的任務。
    *   在呼叫函式後，檢查資料庫中的任務狀態是否已變為 `completed`，且 `result_text` 欄位有內容。
*   **使用技術**: `pytest`, `sqlite3`

### `ignition_test.py`

*   **職責**: 「點火測試」，確保所有重要的模組都可以被成功匯入。
*   **主要功能**:
    *   嘗試 `import` 所有在 `src` 目錄下的主要模組。
    *   如果任何一個 `import` 失敗，測試就會失敗。
    *   這有助於在早期發現因為路徑問題或依賴問題導致的啟動錯誤。
*   **使用技術**: `pytest`

---

## 技術債掃描

在分析過程中，我們識別出以下幾個潛在的技術債，如果未來專案要擴展，這些點值得我們投入時間去改善。

### 1. 全域狀態管理 (`src/model_state.py`, `src/queues.py`)

*   **問題**: 目前系統使用全域變數 (`model_instance`, `current_status`) 和全域的共享佇列 (`task_queue`, `result_queue`) 來管理狀態。雖然在目前的規模下是可行的，但這種作法有幾個缺點：
    *   **可測試性差**: 任何需要存取這些全域變數的模組，在測試時都很難被隔離。我們需要做很多 mock 或 patch 才能進行單元測試。
    *   **可讀性與維護性**: 狀態的改變可能發生在程式的任何地方，追蹤起來很困難。
    *   **擴展性受限**: 如果未來需要同時處理多個模型，或是有更複雜的任務佇列邏輯，目前的架構會變得很難擴展。
*   **建議**:
    *   可以考慮將狀態封裝到一個或多個類別中，並使用依賴注入 (Dependency Injection) 的方式將這些狀態物件傳遞給需要的模組。FastAPI 對依賴注入有很好的支援。
    *   例如，可以建立一個 `AppState` 類別來管理 `model_instance` 和 `status`，然後在 FastAPI 的 `lifespan` 中建立這個物件，並透過 `Depends` 將它注入到 API 端點中。

### 2. 工人 (Worker) 的職責不單一 (`src/transcriber_worker.py`)

*   **問題**: 目前的 `transcriber_worker_process` 函式做了太多事情：
    1.  從佇列中取得任務。
    2.  與資料庫互動，更新任務狀態。
    3.  呼叫 AI 模型進行轉寫。
    4.  將結果放回另一個佇列。
*   **建議**:
    *   可以將這些職責拆分成更小的函式或類別。例如：
        *   一個 `DatabaseManager` 類別，專門負責所有資料庫的操作。
        *   一個 `TranscriptionService` 類別，專門負責呼叫 `faster-whisper` 模型。
    *   這樣可以讓 `transcriber_worker_process` 的邏輯變得更清晰，也更容易對每個部分進行單獨的測試。

### 3. 設定與程式碼耦合

*   **問題**: 有一些設定是直接寫在程式碼中的，例如 `UPLOAD_DIR` 在 `database.py` 中被定義。
*   **建議**:
    *   將所有可設定的參數都移到 `config.py` 中，讓設定集中管理。這樣未來如果需要修改路徑或其他設定，只需要改一個地方。

### 4. 缺乏詳細的 API 文件

*   **問題**: FastAPI 內建了強大的 OpenAPI (Swagger) 文件產生功能，但目前的 API 端點缺乏詳細的註解 (例如：`description`, `responses`)。
*   **建議**:
    *   在 `main.py` 的 API 端點上，可以加上更詳細的 docstring 或 `description` 參數，並定義可能的回應 (responses)。這樣不僅可以讓自動產生的文件更完整，也可以讓其他開發者更容易理解如何使用這些 API。

### 5. `commander_console.py` 與 `main.py` 的重複邏輯

*   **問題**: `commander_console.py` 在啟動 `run-server` 時，會直接呼叫 `uvicorn.run("src.main:app", ...)`。而 `src/main.py` 內部也有自己的啟動邏輯 (雖然主要是 `lifespan`)。
*   **建議**:
    *   可以考慮將 FastAPI app 的建立過程封裝成一個工廠函式 (Factory Function)，例如 `create_app()`。這樣 `commander_console.py` 和直接執行 `uvicorn` 都可以呼叫這個函式來取得 app 實例，確保啟動邏輯的一致性。
