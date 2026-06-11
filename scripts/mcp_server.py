from __future__ import annotations

import os
import sys
import time
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings  # noqa: E402
from app.local_status import collect_local_status, recover_search_backend  # noqa: E402
from app.mcp_payload import format_mcp_research_payload  # noqa: E402
from app.observability import configure_logging, log_research_result  # noqa: E402
from app.pipeline import collect_research_context  # noqa: E402


os.environ.setdefault("LOCAL_REALTIME_SEARCH_LOG_FILE", str(PROJECT_ROOT / ".cache" / "mcp-events.jsonl"))
configure_logging()
mcp = FastMCP("local-realtime-search", json_response=True)

_RECENT_RESULT_TTL_SECONDS = 120.0
_RECENT_RESULTS: dict[tuple[str, str, str], tuple[float, dict[str, Any]]] = {}
_QUESTION_NOISE = {
    "latest",
    "news",
    "updated",
    "detailed",
    "comprehensive",
    "report",
    "summary",
    "brief",
    "overview",
    "analysis",
}


def _question_fingerprint(question: str) -> str:
    tokens = re.findall(r"[\w\uac00-\ud7a3]+", question.lower())
    kept = [token for token in tokens if token not in _QUESTION_NOISE]
    return " ".join(kept)[:500]


def _recent_key(question: str, mode: str, freshness: str | None) -> tuple[str, str, str]:
    return (_question_fingerprint(question), (mode or "fast").lower().strip(), freshness or "")


def _get_recent_payload(key: tuple[str, str, str]) -> dict[str, Any] | None:
    now = time.monotonic()
    stale = [item_key for item_key, (created, _) in _RECENT_RESULTS.items() if now - created > _RECENT_RESULT_TTL_SECONDS]
    for item_key in stale:
        _RECENT_RESULTS.pop(item_key, None)
    cached = _RECENT_RESULTS.get(key)
    if cached is None:
        return None
    payload = deepcopy(cached[1])
    warnings = list(payload.get("warnings", []))
    warnings.append("Reused the previous local_research result for a near-duplicate tool call to avoid repeated search loops.")
    payload["warnings"] = warnings
    payload["duplicate_tool_call"] = True
    return payload


@mcp.tool()
async def local_research(
    question: str,
    ctx: Context,
    mode: str = "auto",
    freshness: str | None = None,
) -> dict[str, Any]:
    """Collect fresh web evidence, citations, source links, and provider health for a user question."""
    key = _recent_key(question, mode, freshness)
    cached_payload = _get_recent_payload(key)
    if cached_payload is not None:
        await ctx.info("Reusing recent local_research result for a near-duplicate request")
        return cached_payload

    await ctx.info(f"Planning local research for: {question}")
    await ctx.report_progress(progress=0.1, total=1.0, message="Planning and searching")
    context = await collect_research_context(
        question,
        mode=mode,
        freshness=freshness,
        settings=get_settings(),
    )
    log_research_result("mcp.local_research", context)
    await ctx.report_progress(progress=1.0, total=1.0, message="Research context ready")
    payload = format_mcp_research_payload(context)
    _RECENT_RESULTS[key] = (time.monotonic(), deepcopy(payload))
    return payload


@mcp.tool()
async def local_status(
    ctx: Context,
    include_logs: bool = True,
) -> dict[str, Any]:
    """Diagnose Docker, SearXNG, API/UI, config, and recent MCP startup logs."""
    await ctx.info("Checking local realtime search status")
    return await collect_local_status(
        settings=get_settings(),
        project_root=PROJECT_ROOT,
        include_logs=include_logs,
    )


@mcp.tool()
async def local_recover(
    ctx: Context,
    include_api: bool = False,
) -> dict[str, Any]:
    """Start Docker/SearXNG, optionally API/UI, then return fresh backend diagnostics."""
    await ctx.info("Starting local realtime search backend")
    return await recover_search_backend(
        settings=get_settings(),
        project_root=PROJECT_ROOT,
        include_api=include_api,
    )


if __name__ == "__main__":
    mcp.run()
