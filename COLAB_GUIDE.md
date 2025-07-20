# 在 Google Colab 中運行鳳凰專案

本指南將引導您如何在 Google Colab 環境中成功設定並啟動鳳凰錄音轉寫服務。

## 前言

由於 Google Colab 的網路環境限制，我們無法使用專案內建的多行程啟動器 (`commander_console.py`)。我們需要直接啟動 FastAPI 應用程式，並透過一些特殊的程式碼來取得公開的網址。

## 操作步驟

請在您的 Colab 筆記本中，依照以下順序執行三個儲存格的程式碼。

### 步驟一：複製專案並安裝依賴

這個儲存格會從 GitHub 下載專案程式碼，並安裝所有必要的 Python 套件。

```python
# 複製專案原始碼
!git clone https://github.com/your-username/your-repo-name.git
%cd your-repo-name

# 安裝相依套件
!pip install -r requirements.txt
```

**請記得替換 `your-username` 和 `your-repo-name` 為您自己的 GitHub 使用者名稱和專案庫名稱。**

### 步驟二：修改主程式以適應 Colab 環境

這個儲存格會使用 `sed` 指令，自動修改 `src/main.py` 檔案。這個修改的目的是在啟動伺服器之前，先呼叫 Colab 的 `proxyPort` 功能來產生一個公開的網址。

```python
# 使用 sed 指令修改 main.py，以整合 Colab 的連接埠轉發功能
!sed -i 's/uvicorn.run(app, host="0.0.0.0", port=8000)/from google.colab.output import eval_js; print(eval_js("google.colab.kernel.proxyPort(8000)")); uvicorn.run(app, host="0.0.0.0", port=8000)/' src/main.py
```

### 步驟三：啟動伺服器

這個儲存格會執行 `src/main.py`，啟動 FastAPI 伺服器。執行後，您會在儲存格的輸出中看到一個 `https://...` 開頭的網址，這就是您可以存取的公開服務網址。

```python
# 啟動應用程式
!python src/main.py
```

---

## 疑難排解

*   **`ModuleNotFoundError: No module named 'google.colab'`**: 這個錯誤表示您正在一個非 Colab 的環境中執行程式碼。請確保您是在 Google Colab 的筆記本中執行這些指令。
*   **伺服器沒有啟動**: 如果您在執行步驟三後沒有看到網址，請檢查前兩個步驟是否都已成功執行，並且沒有任何錯誤訊息。

如果您遇到任何其他問題，請隨時提出。
