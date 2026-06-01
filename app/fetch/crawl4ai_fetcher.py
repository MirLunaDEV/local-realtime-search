from __future__ import annotations

import asyncio
from typing import Any

from app.fetch.http_fetcher import FetchedPage


class Crawl4AiUnavailableError(RuntimeError):
    pass


async def fetch_page_with_crawl4ai(url: str, timeout_seconds: float = 8.0) -> FetchedPage:
    try:
        from crawl4ai import AsyncWebCrawler  # type: ignore
    except Exception as exc:
        raise Crawl4AiUnavailableError("crawl4ai is not installed. Install the optional crawl4ai extra.") from exc

    async def _run() -> FetchedPage:
        async with AsyncWebCrawler() as crawler:
            result: Any = await crawler.arun(url=url)
        markdown = str(getattr(result, "markdown", "") or "")
        cleaned_markdown = markdown.strip()
        if not cleaned_markdown:
            raise RuntimeError("Crawl4AI returned empty markdown.")
        title = str(getattr(result, "metadata", {}).get("title", "") if getattr(result, "metadata", None) else "")
        return FetchedPage(url=url, title=title, text=cleaned_markdown, status_code=200)

    return await asyncio.wait_for(_run(), timeout=timeout_seconds)

