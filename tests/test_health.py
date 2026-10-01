"""Tests for FormatAI FastAPI backend health and root endpoints."""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify root endpoint returns Python FastAPI operational message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "FormatAI"
    assert "FastAPI" in data["backend"]
    assert "running successfully" in data["message"]


def test_health_check_endpoint():
    """Verify /api/health returns the exact required schema:

    {
      "status": "ok",
      "service": "FormatAI",
      "backend": "python"
    }
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "status": "ok",
        "service": "FormatAI",
        "backend": "python",
    }
