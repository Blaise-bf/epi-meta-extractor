from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_schema_endpoint():
    response = client.get("/schema")

    assert response.status_code == 200
    body = response.json()
    assert "metadata" in body
    assert "methods" in body
    assert "analysis" in body

