import uvicorn
from src.main import app

if __name__ == "__main__":
    print(">>> 正在啟動 Uvicorn 伺服器...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
