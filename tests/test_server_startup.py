import pytest
import httpx

def test_server_startup(live_api_server):
    """
    A minimal test to verify that the live_api_server fixture can start the server.
    """
    base_url = live_api_server
    response = httpx.get(f"{base_url}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
