from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_docker_compose_defines_optional_api_profile() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "api:" in compose
    assert "profiles:" in compose
    assert "pull_policy: build" in compose
    assert "LM_STUDIO_BASE_URL=${DOCKER_LM_STUDIO_BASE_URL:-http://host.docker.internal:1234/v1}" in compose
    assert "SEARXNG_BASE_URL=http://searxng:8080" in compose
    assert "condition: service_healthy" in compose
    assert "local-realtime-cache:" in compose


def test_dockerfile_runs_uvicorn_app() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "python:3.12-slim" in dockerfile
    assert "uv sync --frozen --no-dev" in dockerfile
    assert 'CMD ["/app/.venv/bin/uvicorn", "app.main:app"' in dockerfile


def test_windows_helper_can_start_api_profile() -> None:
    script = (ROOT / "scripts" / "start_search_backend.ps1").read_text(encoding="utf-8")

    assert "param(" in script
    assert "[switch]$Api" in script
    assert "docker compose --profile api up -d searxng api" in script
    assert "http://127.0.0.1:8787/health" in script
