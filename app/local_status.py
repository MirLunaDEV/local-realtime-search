from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import time
from pathlib import Path

import httpx

from app.config import Settings
from app.config_validation import validate_settings
from app.search_backend_health import check_search_backend


def _trim(value: str, limit: int = 500) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def _run_command(args: list[str], *, cwd: Path, timeout_seconds: float = 5.0) -> dict[str, object]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        return {
            "status": "missing",
            "returncode": None,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "error": _trim(str(exc) or exc.__class__.__name__),
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "returncode": None,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "error": f"Command timed out after {timeout_seconds:g}s.",
        }

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    return {
        "status": "ok" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "stdout": _trim(stdout),
        "stderr": _trim(stderr),
    }


def _append_log(path: Path, *, label: str, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(
        {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "label": label,
            "payload": payload,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(rendered + "\n")


def _parse_compose_ps(text: str) -> list[dict[str, object]]:
    if not text.strip():
        return []
    try:
        payload = json.loads(text)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            return [payload]
    except json.JSONDecodeError:
        pass

    items: list[dict[str, object]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            items.append(item)
    return items


def _check_docker(project_root: Path) -> dict[str, object]:
    version = _run_command(["docker", "version", "--format", "{{.Server.Version}}"], cwd=project_root)
    engine_ok = version["status"] == "ok" and bool(str(version.get("stdout") or "").strip())
    result: dict[str, object] = {
        "engine_status": "ok" if engine_ok else "down",
        "server_version": str(version.get("stdout") or "") if engine_ok else None,
        "version_check": version,
    }
    if not engine_ok:
        result["diagnosis"] = "Docker engine is not reachable. Docker Desktop is probably closed or still starting."
        return result

    compose = _run_command(["docker", "compose", "ps", "--format", "json"], cwd=project_root)
    result["compose_check"] = compose
    result["compose_services"] = _parse_compose_ps(str(compose.get("stdout") or "")) if compose["status"] == "ok" else []
    return result


def _recover_backend_command(project_root: Path, *, include_api: bool) -> list[str]:
    powershell = shutil.which("powershell.exe") or shutil.which("powershell") or "powershell.exe"
    script = project_root / "scripts" / "start_search_backend.ps1"
    args = [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]
    if include_api:
        args.append("-Api")
    return args


async def _check_api_health(url: str = "http://127.0.0.1:8787/health") -> dict[str, object]:
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
            response = await client.get(url)
    except Exception as exc:
        return {
            "status": "down",
            "url": url,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "error": _trim(str(exc) or exc.__class__.__name__),
            "required_for_mcp": False,
        }

    payload: object
    try:
        payload = response.json()
    except Exception:
        payload = response.text[:500]
    return {
        "status": "ok" if 200 <= response.status_code < 500 else "down",
        "url": url,
        "status_code": response.status_code,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "payload": payload,
        "required_for_mcp": False,
    }


def _tail_file(path: Path, *, lines: int, chars: int = 6000) -> dict[str, object]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "tail": [],
        }
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            "path": str(path),
            "exists": True,
            "tail": [],
            "error": _trim(str(exc) or exc.__class__.__name__),
        }
    if len(text) > chars:
        text = text[-chars:]
    return {
        "path": str(path),
        "exists": True,
        "tail": text.splitlines()[-lines:],
    }


def _recommended_actions(
    *,
    docker_status: dict[str, object],
    search_status: dict[str, object],
    startup_log: dict[str, object],
) -> list[str]:
    actions: list[str] = []
    if docker_status.get("engine_status") != "ok":
        actions.append("Start Docker Desktop, or restart LM Studio after using the auto-start MCP config.")
        actions.append("Run .\\scripts\\start_search_backend.ps1 from the project root to start SearXNG manually.")
    if search_status.get("status") == "down":
        actions.append("SearXNG is unreachable. Check Docker Desktop and run docker compose up -d searxng.")
    elif search_status.get("status") == "empty":
        actions.append("SearXNG is reachable but returned no results. Retry later or rely on direct fallback providers.")
    elif search_status.get("status") == "degraded":
        actions.append("SearXNG is reachable but some upstream engines are unavailable; fallback providers can still collect evidence.")
    if not startup_log.get("exists"):
        actions.append("No MCP startup log was found. LM Studio may still be using the old direct mcp_server.py config.")
    return actions


async def recover_search_backend(
    *,
    settings: Settings,
    project_root: Path,
    include_api: bool = False,
    timeout_seconds: float = 240.0,
) -> dict[str, object]:
    """Start Docker/SearXNG using the Windows helper script, then return fresh diagnostics."""
    command = _recover_backend_command(project_root, include_api=include_api)
    recovery = await asyncio.to_thread(
        _run_command,
        command,
        cwd=project_root,
        timeout_seconds=timeout_seconds,
    )
    _append_log(project_root / ".cache" / "local-recover.jsonl", label="recover_search_backend", payload=recovery)

    search_backend = await check_search_backend(settings)
    api_status = await _check_api_health() if include_api else {"status": "not_checked", "required_for_mcp": False}
    status = "ok" if recovery.get("status") == "ok" and search_backend.status in {"ok", "degraded", "empty"} else "failed"
    recommended_actions: list[str] = []
    if status != "ok":
        recommended_actions.extend(
            [
                "Open Docker Desktop manually and wait until the engine is ready.",
                "Run .\\scripts\\start_search_backend.ps1 from the project root.",
                "Then call local_status again to verify the backend.",
            ]
        )
    elif search_backend.status == "degraded":
        recommended_actions.append(
            "SearXNG is running, but some upstream engines are unavailable; fallback providers can still collect evidence."
        )

    return {
        "tool": "local_recover",
        "overall_status": status,
        "action": "start_search_backend",
        "include_api": include_api,
        "instruction_to_model": (
            "Summarize whether recovery succeeded in the user's language. If overall_status is ok, tell the user "
            "that local_research can be retried. If failed, show the recommended actions and mention the recovery log."
        ),
        "command": {
            "program": command[0],
            "args": command[1:],
            "cwd": str(project_root),
        },
        "recovery": recovery,
        "checks": {
            "searxng": search_backend.to_dict(),
            "api_ui": api_status,
        },
        "logs": {
            "recovery": str(project_root / ".cache" / "local-recover.jsonl"),
            "startup": str(project_root / ".cache" / "mcp-startup.log"),
        },
        "recommended_actions": recommended_actions,
    }


def _diagnosis(
    *,
    docker_status: dict[str, object],
    search_status: dict[str, object],
    api_status: dict[str, object],
    startup_log: dict[str, object],
) -> tuple[str, str]:
    if docker_status.get("engine_status") != "ok":
        return "down", "Docker engine is not reachable, so SearXNG cannot be started or inspected."
    if search_status.get("status") == "down":
        return "down", "SearXNG is not reachable at the configured SEARXNG_BASE_URL."
    if search_status.get("status") in {"empty", "degraded"}:
        return "degraded", "SearXNG is reachable, but search coverage is weak or partially unavailable."
    if not startup_log.get("exists"):
        return "degraded", "Core search is reachable, but the MCP auto-start wrapper does not appear to have run yet."
    if api_status.get("status") == "down":
        return "ok", "MCP search is ready. The API/UI service is down, but it is not required for LM Studio MCP."
    return "ok", "Local realtime search is ready."


async def collect_local_status(
    *,
    settings: Settings,
    project_root: Path,
    include_logs: bool = True,
    log_lines: int = 20,
) -> dict[str, object]:
    """Collect local diagnostics for the LM Studio MCP integration."""
    docker_task = asyncio.to_thread(_check_docker, project_root)
    search_task = check_search_backend(settings)
    api_task = _check_api_health()
    docker_status, search_backend, api_status = await asyncio.gather(docker_task, search_task, api_task)

    startup_log = _tail_file(project_root / ".cache" / "mcp-startup.log", lines=log_lines) if include_logs else {}
    event_log = _tail_file(project_root / ".cache" / "mcp-events.jsonl", lines=log_lines) if include_logs else {}
    search_status = search_backend.to_dict()
    overall_status, diagnosis = _diagnosis(
        docker_status=docker_status,
        search_status=search_status,
        api_status=api_status,
        startup_log=startup_log,
    )
    actions = _recommended_actions(
        docker_status=docker_status,
        search_status=search_status,
        startup_log=startup_log,
    )

    return {
        "tool": "local_status",
        "overall_status": overall_status,
        "diagnosis": diagnosis,
        "instruction_to_model": (
            "Summarize this diagnostic result in the user's language. Explain the likely cause first, then give the "
            "recommended actions. Do not call local_research just to verify status."
        ),
        "checks": {
            "docker": docker_status,
            "searxng": search_status,
            "api_ui": api_status,
            "config": validate_settings(settings),
        },
        "logs": {
            "startup": startup_log,
            "events": event_log,
        }
        if include_logs
        else {},
        "recommended_actions": actions,
    }
