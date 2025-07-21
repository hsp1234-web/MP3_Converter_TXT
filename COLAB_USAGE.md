# 在 Google Colab 中啟動服務 - 詳細教學

這份文件將引導您如何透過 Google Colab，用最簡單的方式啟動我們的錄音轉寫服務。

---

## 步驟一：開啟 Colab 部署腳本

您有兩種方式可以開啟部署腳本：

1.  **(推薦) 點擊連結直接開啟**：
    [![在 Colab 中開啟](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/hsp1234-web/MP3_Converter_TXT/blob/main/colab_deployment_script.py)
    點擊上方按鈕，會直接在新的瀏覽器分頁中，為您載入我們預設的 Colab 部署腳本。

2.  **手動上傳**：
    a. 前往 [Google Colab](https://colab.research.google.com/)。
    b. 點擊 `File -> Upload notebook`。
    c. 選擇我們專案中的 `colab_deployment_script.py` 檔案並上傳。

---

## 步驟二：設定作戰參數

在 Colab 頁面中，您會看到一些可以客製化的選項。

- **REPOSITORY_URL**: 預設會是我們專案的 GitHub 位置。如果您有自己的分支版本 (fork)，可以替換成您的倉庫網址。
- **TARGET_BRANCH**: 指定要使用的程式碼分支。通常維持 `main` 即可。
- **MODEL_SIZE**: 選擇您想使用的 AI 轉錄模型大小。
  - `base`: (預設) 平衡速度與準確率，推薦初次使用者。
  - `tiny`: 最快，但準確率較低。
  - `small`, `medium`, `large-v3`: 更大、更準確，但需要更長的載入和處理時間。
- **FORCE_REPO_REFRESH**: 如果勾選此項，每次啟動時都會重新從 GitHub 下載最新的程式碼。若您不確定，建議勾選。

---

## 步驟三：啟動服務

設定好參數後，有兩種方式可以執行：

1.  點擊第一個儲存格 (cell) 左側的 **「執行」按鈕 (▶️)**。
2.  使用快捷鍵 `Ctrl + Enter` (或 `Cmd + Enter` on Mac) 來執行當前儲存格。

執行後，您會看到下方的日誌開始滾動。腳本會自動完成以下所有事情：
- 環境準備
- 下載專案程式碼
- 安裝所有需要的套件
- 啟動網頁伺服器

這個過程可能需要數分鐘，特別是第一次執行時，因為需要下載 AI 模型。

---

## 步驟四：取得並使用服務網址

當一切準備就緒後，頁面會自動刷新，並顯示一個綠色的成功訊息框。

![成功畫面截圖](https://i.imgur.com/your-success-image.png)  <!-- 這裡可以放一個示意圖 -->

點擊訊息框中的 **「🚀 開啟鳳凰轉錄儀指揮中心 🚀」** 按鈕，即可在新分頁中開啟服務介面，開始上傳錄音檔進行轉寫。

這個網址是公開的，您也可以分享給其他人使用 (只要您的 Colab 執行緒還在運作中)。

---

## 步驟五：停止服務

當您使用完畢後，**務必回到 Colab 頁面，點擊執行按鈕旁邊的「中斷執行」(■) 方塊**。

這會確實關閉所有背景服務，釋放 Colab 的運算資源。如果您忘記這個步驟，Colab 也會在閒置一段時間後自動中斷。

---

## 疑難排解

- **出現錯誤訊息**: 請仔細閱讀 Colab 頁面下方的日誌輸出，通常會包含錯誤的原因。您可以嘗試重新執行一次，或是在專案的 GitHub Issues 中提出問題。
- **網址無法開啟**: 請確認 Colab 的執行緒是否還在運作中。如果已經中斷，您需要重新執行一次腳本來取得新的網址。
