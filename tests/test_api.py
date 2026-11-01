# tests/test_api.py

from fastapi.testclient import TestClient

from model_service.app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
