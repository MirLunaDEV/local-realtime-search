from __future__ import annotations

from urllib.parse import urljoin

import httpx

from app.search.base import SearchResult


class SearxngProvider:
    name = "searxng"

    def __init__(self, base_url: str, timeout_seconds: float = 2.5) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def search(self, query: str, *, freshness: str | None = None, limit: int = 10) -> list[SearchResult]:
        params: dict[str, str | int] = {
            "q": query,
            "format": "json",
            "language": "auto",
            "safesearch": 0,
        }
        if freshness:
            params["time_range"] = freshness

        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = await client.get(urljoin(self.base_url + "/", "search"), params=params)
            response.raise_for_status()
            payload = response.json()

        results: list[SearchResult] = []
        for index, item in enumerate(payload.get("results", [])[:limit], start=1):
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            results.append(
                SearchResult(
                    title=str(item.get("title") or url),
                    url=url,
                    snippet=str(item.get("content") or ""),
                    provider=self.name,
                    rank=index,
                    published_or_updated=item.get("publishedDate") or item.get("published_date"),
                )
            )
        return results

