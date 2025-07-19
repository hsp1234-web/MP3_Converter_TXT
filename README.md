# 系統能力清單 (System Capabilities)

本文件是專案的「活的儀表板」。此處列出了所有核心能力，並提供可直接複製執行的命令。

所有後台任務、數據處理、模型訓練等功能，其唯一的啟動入口皆為 `commander_console.py`。
在終端機輸入 `python commander_console.py --help` 即可列出系統具備的所有離線作戰能力。

---

## 主要能力

| 功能描述 | 命令 |
|:---|:---|
| **啟動完整的 API 服務 (測試模式)** | `python commander_console.py run-server --profile=testing` |
| **啟動完整的 API 服務 (生產模式)** | `python commander_console.py run-server --profile=production` |
| **執行所有自動化測試** | `python commander_console.py run-tests` |
| **安裝/更新所有專案依賴** | `python commander_console.py install-deps` |
