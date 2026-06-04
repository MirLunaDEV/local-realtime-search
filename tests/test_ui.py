from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


def test_index_serves_local_research_ui() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Local Realtime Search" in response.text
    assert "/ask/stream" in response.text


def test_health_includes_config_status(monkeypatch) -> None:
    class FakeBackend:
        status = "ok"

        def to_dict(self) -> dict[str, object]:
            return {"provider": "searxng", "status": "ok"}

    async def fake_check_search_backend(settings):
        return FakeBackend()

    monkeypatch.setattr(main_module, "check_search_backend", fake_check_search_backend)

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert "config" in payload
    assert payload["config"]["status"] in {"ok", "warning", "error"}


def test_health_warning_config_does_not_degrade_status(monkeypatch) -> None:
    class FakeBackend:
        status = "ok"

        def to_dict(self) -> dict[str, object]:
            return {"provider": "searxng", "status": "ok"}

    async def fake_check_search_backend(settings):
        return FakeBackend()

    monkeypatch.setattr(main_module, "check_search_backend", fake_check_search_backend)

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
