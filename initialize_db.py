#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
【資料庫初始化腳本】
此腳本的唯一職責是調用核心模組中的 initialize_database 函數。
它被設計為在主服務啟動之前，在 shell 腳本中被調用。
"""
import asyncio
import logging
import sys
import os

# 確保 src 目錄在 Python 路徑中
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.core import initialize_database

# 為了在腳本執行時能看到日誌，這裡做一個簡單的配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')

async def main():
    """執行資料庫初始化。"""
    logging.info("--- [資料庫初始化]：開始 ---")
    try:
        await initialize_database()
        logging.info("--- [資料庫初始化]：成功 ---")
    except Exception as e:
        logging.error("--- [資料庫初始化]：失敗 ---")
        logging.error("錯誤詳情: %s", e, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
