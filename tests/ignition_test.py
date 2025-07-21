from __future__ import annotations

"""點火測試, 確保所有模組都可以被導入."""
import pytest

from src import core, main, mock_worker, queues, transcriber_worker
from src.core import hardware


def test_import_all() -> None:
    """測試所有模組是否可以被導入."""
    try:
        assert core
        assert main
        assert mock_worker
        assert queues
        assert transcriber_worker
        assert hardware
    except (ImportError, ModuleNotFoundError) as e:
        pytest.fail(f"Failed to import modules: {e}")
