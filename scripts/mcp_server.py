from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP

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
