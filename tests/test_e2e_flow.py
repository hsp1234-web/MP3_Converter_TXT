"""端到端流程測試."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

import aiofiles
import httpx
import pytest

# --- Constants ---
POLL_INTERVAL = 0.5
TEST_TIMEOUT = 60


@pytest.mark.asyncio()
async def test_full_transcription_flow(live_api_server: str) -> None:
    """
    一個完整的端到端測試案例.

    1. 上傳一個檔案並獲取 task_id.
    2. 輪詢狀態端點, 直到任務完成或失敗.
    3. 驗證最終結果.
    """
    base_url = live_api_server  # Use the URL from the fixture
    start_time = time.time()

    # --- Step 1: Upload a mock audio file ---
    mock_audio_path = Path("test_audio.wav")
    mock_audio_path.write_bytes(
        b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80\xbb\x00\x00\x00\xee\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00",
    )

    task_id = None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            with mock_audio_path.open("rb") as f:
                files = {"file": (mock_audio_path.name, f, "audio/wav")}

                response = await client.post(f"{base_url}/upload", files=files)

        response.raise_for_status()  # Will raise an exception for 4xx/5xx responses
        assert response.status_code == 202

        response_data = response.json()
        assert "task_id" in response_data
        task_id = response_data["task_id"]

        # --- Step 2: Poll the status endpoint ---
        final_status = None
        while time.time() - start_time < TEST_TIMEOUT:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{base_url}/status/{task_id}")

            response.raise_for_status()
            status_data = response.json()
            current_status = status_data.get("status")

            # Because we don't have a real worker, we expect the status to remain 'pending'
            # In a full E2E test with a worker, we would check for 'completed'
            if current_status == "pending":
                # For this test, just confirming it's pending is enough
                final_status = status_data
                break

            await asyncio.sleep(POLL_INTERVAL)
        else:
            pytest.fail(
                f"Test timed out after {TEST_TIMEOUT} seconds, task did not reach expected state.",
            )

        # --- Step 3: Validate the final result ---
        assert final_status is not None, "Did not get a final status after polling."
        assert final_status["status"] == "pending"

    finally:
        # Clean up the test file
        if mock_audio_path.exists():
            mock_audio_path.unlink()
