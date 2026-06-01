from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.mcp_payload import format_mcp_research_payload
from app.pipeline import collect_research_context


mcp = FastMCP("local-realtime-search", json_response=True)


@mcp.tool()
async def local_research(
    question: str,
    ctx: Context,
    mode: str = "fast",
    freshness: str | None = None,
) -> dict[str, Any]:
    """Collect fresh web evidence, citations, source links, and provider health for a user question."""
    await ctx.info(f"Planning local research for: {question}")
    await ctx.report_progress(progress=0.1, total=1.0, message="Planning and searching")
    context = await collect_research_context(
        question,
        mode=mode,
        freshness=freshness,
        settings=get_settings(),
    )
    await ctx.report_progress(progress=1.0, total=1.0, message="Research context ready")
    return format_mcp_research_payload(context)


if __name__ == "__main__":
    mcp.run()
