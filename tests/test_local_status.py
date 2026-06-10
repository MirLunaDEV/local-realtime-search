from __future__ import annotations

from pathlib import Path

import pytest

from app import local_status
from app.config import Settings
from app.search_backend_health import SearchBackendStatus


async def _fake_api_ok() -> dict[str, object]:
    return {"status": "ok", "required_for_mcp": False}


def test_parse_compose_ps_accepts_json_lines() -> None:
    text = '{"Service":"searxng","State":"running"}\n{"Service":"api","State":"running"}\n'

    services = local_status._parse_compose_ps(text)

    assert [item["Service"] for item in services] == ["searxng", "api"]


@pytest.mark.anyio
async def test_collect_local_status_reports_ready(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache = tmp_path / ".cache"
    cache.mkdir()
    (cache / "mcp-startup.log").write_text("Docker engine is ready.\nSearXNG health check HTTP status: 200\n")
    (cache / "mcp-events.jsonl").write_text('{"event":"mcp.local_research"}\n')

    async def fake_search(settings: Settings) -> SearchBackendStatus:
        return SearchBackendStatus(
            provider="searxng",
            status="ok",
            base_url=settings.searxng_base_url,
            elapsed_ms=12,
            result_count=5,
        )

    monkeypatch.setattr(local_status, "check_search_backend", fake_search)
    monkeypatch.setattr(
        local_status,
        "_check_docker",
        lambda project_root: {"engine_status": "ok", "server_version": "28.5.1", "compose_services": []},
    )
    monkeypatch.setattr(local_status, "_check_api_health", _fake_api_ok)

    payload = await local_status.collect_local_status(
        settings=Settings(),
        project_root=tmp_path,
    )

    assert payload["tool"] == "local_status"
    assert payload["overall_status"] == "ok"
    assert payload["checks"]["searxng"]["status"] == "ok"  # type: ignore[index]
    assert payload["logs"]["startup"]["exists"] is True  # type: ignore[index]
    assert payload["recommended_actions"] == []


@pytest.mark.anyio
async def test_collect_local_status_reports_docker_down(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    async def fake_search(settings: Settings) -> SearchBackendStatus:
        return SearchBackendStatus(
            provider="searxng",
            status="down",
            base_url=settings.searxng_base_url,
            elapsed_ms=2000,
            error="connect failed",
        )

    monkeypatch.setattr(local_status, "check_search_backend", fake_search)
    monkeypatch.setattr(
        local_status,
        "_check_docker",
        lambda project_root: {"engine_status": "down", "diagnosis": "Docker Desktop is closed."},
    )
    monkeypatch.setattr(local_status, "_check_api_health", _fake_api_ok)

    payload = await local_status.collect_local_status(
        settings=Settings(),
        project_root=tmp_path,
    )

    actions = payload["recommended_actions"]
    assert payload["overall_status"] == "down"
    assert "Docker engine is not reachable" in str(payload["diagnosis"])
    assert any("Docker Desktop" in str(action) for action in actions)  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_collect_local_status_reports_degraded_without_startup_log(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def fake_search(settings: Settings) -> SearchBackendStatus:
        return SearchBackendStatus(
            provider="searxng",
            status="degraded",
            base_url=settings.searxng_base_url,
            elapsed_ms=12,
            result_count=3,
            error="duckduckgo unresponsive",
        )

    monkeypatch.setattr(local_status, "check_search_backend", fake_search)
    monkeypatch.setattr(local_status, "_check_docker", lambda project_root: {"engine_status": "ok"})
    monkeypatch.setattr(local_status, "_check_api_health", _fake_api_ok)

    payload = await local_status.collect_local_status(
        settings=Settings(),
        project_root=tmp_path,
    )

    assert payload["overall_status"] == "degraded"
    assert payload["checks"]["searxng"]["status"] == "degraded"  # type: ignore[index]
    assert any("fallback providers" in str(action) for action in payload["recommended_actions"])  # type: ignore[arg-type]


def test_run_command_handles_missing_binary(tmp_path: Path) -> None:
    result = local_status._run_command(["definitely-not-a-real-local-status-command"], cwd=tmp_path)

    assert result["status"] == "missing"
    assert result["error"]


def test_recover_backend_command_can_include_api(tmp_path: Path) -> None:
    command = local_status._recover_backend_command(tmp_path, include_api=True)

    assert command[1:5] == ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
    assert command[-1] == "-Api"
    assert "start_search_backend.ps1" in command[-2]


@pytest.mark.anyio
async def test_recover_search_backend_reports_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    commands: list[list[str]] = []

    def fake_run_command(args: list[str], **kwargs: object) -> dict[str, object]:
        commands.append(args)
        return {"status": "ok", "returncode": 0, "stdout": "SearXNG health check HTTP status: 200"}

    async def fake_search(settings: Settings) -> SearchBackendStatus:
        return SearchBackendStatus(
            provider="searxng",
            status="ok",
            base_url=settings.searxng_base_url,
            elapsed_ms=10,
            result_count=5,
        )

    monkeypatch.setattr(local_status, "_run_command", fake_run_command)
    monkeypatch.setattr(local_status, "check_search_backend", fake_search)

    payload = await local_status.recover_search_backend(
        settings=Settings(),
        project_root=tmp_path,
        include_api=False,
    )

    assert payload["tool"] == "local_recover"
    assert payload["overall_status"] == "ok"
    assert commands
    assert (tmp_path / ".cache" / "local-recover.jsonl").exists()


@pytest.mark.anyio
async def test_recover_search_backend_reports_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_run_command(args: list[str], **kwargs: object) -> dict[str, object]:
        return {"status": "failed", "returncode": 1, "stderr": "docker unavailable"}

    async def fake_search(settings: Settings) -> SearchBackendStatus:
        return SearchBackendStatus(
            provider="searxng",
            status="down",
            base_url=settings.searxng_base_url,
            elapsed_ms=10,
            error="connect failed",
        )

    monkeypatch.setattr(local_status, "_run_command", fake_run_command)
    monkeypatch.setattr(local_status, "check_search_backend", fake_search)

    payload = await local_status.recover_search_backend(
        settings=Settings(),
        project_root=tmp_path,
    )

    assert payload["overall_status"] == "failed"
    assert payload["recommended_actions"]
