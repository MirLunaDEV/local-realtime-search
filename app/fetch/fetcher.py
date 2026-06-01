from __future__ import annotations

from app.fetch.crawl4ai_fetcher import fetch_page_with_crawl4ai
from app.fetch.http_fetcher import FetchedPage, fetch_page


def _looks_low_quality(page: FetchedPage) -> bool:
    text = page.text.strip()
    if len(text) < 500:
        return True
    replacementish = text.count("?") + text.count("\ufffd")
    return replacementish > max(20, len(text) // 80)


async def fetch_page_best_effort(
    url: str,
    *,
    fetcher: str = "auto",
    http_timeout_seconds: float = 3.0,
    crawl4ai_timeout_seconds: float = 8.0,
) -> tuple[FetchedPage, str]:
    selected = fetcher.lower().strip()

    if selected == "http":
        return await fetch_page(url, timeout_seconds=http_timeout_seconds), "http"

    if selected == "crawl4ai":
        return await fetch_page_with_crawl4ai(url, timeout_seconds=crawl4ai_timeout_seconds), "crawl4ai"

    http_error: Exception | None = None
    try:
        page = await fetch_page(url, timeout_seconds=http_timeout_seconds)
        if not _looks_low_quality(page):
            return page, "http"
    except Exception as exc:
        http_error = exc
        page = None

    try:
        return await fetch_page_with_crawl4ai(url, timeout_seconds=crawl4ai_timeout_seconds), "crawl4ai"
    except Exception:
        if page is not None:
            return page, "http_low_quality"
        if http_error is not None:
            raise http_error
        raise

