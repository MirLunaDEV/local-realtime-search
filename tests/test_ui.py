from fastapi.testclient import TestClient

from app.main import app


def test_index_serves_local_research_ui() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Local Realtime Search" in response.text
    assert "/ask/stream" in response.text
