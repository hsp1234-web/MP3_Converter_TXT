import pytest
from xprocess import ProcessStarter
import sys
from pathlib import Path

@pytest.fixture(scope="session")
def live_server(xprocess):
    """
    A session-scoped fixture that starts the FastAPI server on a fixed port.
    It ensures the server is ready before tests run and handles teardown.
    """

    class Starter(ProcessStarter):
        # Pattern to match in the server's output to confirm it's ready.
        pattern = "Application startup complete"

        # Increase the timeout to give the server enough time to start.
        timeout = 120

        # Command to start the uvicorn server on a fixed port.
        args = [
            sys.executable,
            "-m",
            "uvicorn",
            "src.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8765", # Use a fixed port for simplicity and reliability
        ]

    # The `ensure` function starts the process and waits for the pattern to match.
    xprocess.ensure("live_server", Starter)

    yield

    # Teardown: stop the server process after the test session finishes.
    xprocess.getinfo("live_server").terminate()
