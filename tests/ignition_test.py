import pytest

def test_import_all():
    try:
        from src import launcher
        from src import main
        from src import config
        from src import logger
        from src import queues
        from src import transcriber_worker
        from src import mock_worker
        try:
            from src.core import hardware
        except ModuleNotFoundError:
            pass # 忽略 torch 匯入錯誤
    except ImportError as e:
        pytest.fail(f"Failed to import modules: {e}")
