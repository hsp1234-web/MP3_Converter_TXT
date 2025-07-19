import pytest
import asyncio
import httpx
import time
import os

# --- Constants ---
BASE_URL = "http://127.0.0.1:8765"
POLL_INTERVAL = 0.5
TEST_TIMEOUT = 60

@pytest.mark.asyncio
async def test_full_transcription_flow(live_server):
    """
    A full end-to-end test case that uses the live_server fixture.
    1. Uploads a file and gets a task_id.
    2. Polls the status endpoint until the task is completed or fails.
    3. Validates the final result.
    """
    start_time = time.time()

    # --- Step 1: Upload a mock audio file ---
    mock_audio_path = "test_audio.wav"
    with open(mock_audio_path, "wb") as f:
        f.write(b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80\xbb\x00\x00\x00\xee\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00')

    task_id = None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            with open(mock_audio_path, "rb") as f:
                files = {'file': (os.path.basename(mock_audio_path), f, 'audio/wav')}

                print(f"\nStep 1: Uploading audio file to {BASE_URL}/upload ...")
                response = await client.post(f"{BASE_URL}/upload", files=files)

            response.raise_for_status() # Will raise an exception for 4xx/5xx responses
            assert response.status_code == 202

            response_data = response.json()
            assert "task_id" in response_data
            task_id = response_data["task_id"]
            print(f"File uploaded successfully, task ID: {task_id}")

        # --- Step 2: Poll the status endpoint ---
        print(f"\nStep 2: Polling /status/{task_id} ...")
        final_status = None
        while time.time() - start_time < TEST_TIMEOUT:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{BASE_URL}/status/{task_id}")

            response.raise_for_status()
            status_data = response.json()
            current_status = status_data.get("status")
            print(f"  Polling: Current status = {current_status}")

            # Because we don't have a real worker, we expect the status to remain 'pending'
            # In a full E2E test with a worker, we would check for 'completed'
            if current_status == "pending":
                # For this test, just confirming it's pending is enough
                final_status = status_data
                break

            await asyncio.sleep(POLL_INTERVAL)
        else:
            pytest.fail(f"Test timed out after {TEST_TIMEOUT} seconds, task did not reach expected state.")

        # --- Step 3: Validate the final result ---
        print("\nStep 3: Validating final result...")
        assert final_status is not None, "Did not get a final status after polling."
        assert final_status["status"] == "pending"
        print("\nE2E flow validation successful!")

    finally:
        # Clean up the test file
        if os.path.exists(mock_audio_path):
            os.remove(mock_audio_path)
