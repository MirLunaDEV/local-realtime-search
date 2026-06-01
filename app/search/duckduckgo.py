from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from app.search.base import SearchResult


class _DdgHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_result = False
        self._in_title = False
        self._in_snippet = False
        self._current: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        class_name = attr.get("class") or ""
        if tag == "div" and "result" in class_name:
            self._in_result = True
            self._current = {}
        if not self._in_result:
            return
        if tag == "a" and "result__a" in class_name:
            self._in_title = True
            href = attr.get("href") or ""
            self._current["url"] = _decode_ddg_url(href)
        if tag in {"a", "div"} and "result__snippet" in class_name:
            self._in_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_title:
            self._in_title = False
        if tag in {"a", "div"} and self._in_snippet:
            self._in_snippet = False
        if tag == "div" and self._in_result:
            if self._current.get("url") and self._current.get("title"):
                self.results.append(self._current)
            self._current = {}
            self._in_result = False

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self._current["title"] = f"{self._current.get('title', '')} {text}".strip()
        if self._in_snippet:
            self._current["snippet"] = f"{self._current.get('snippet', '')} {text}".strip()


def _decode_ddg_url(href: str) -> str:
    if href.startswith("//duckduckgo.com/l/"):
        href = "https:" + href
    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    uddg = query.get("uddg")
    if uddg:
        return unquote(uddg[0])
    return href


class DuckDuckGoHtmlProvider:
    name = "duckduckgo_html"

    def __init__(self, timeout_seconds: float = 2.5) -> None:
        self.timeout_seconds = timeout_seconds

    async def search(self, query: str, *, freshness: str | None = None, limit: int = 10) -> list[SearchResult]:
        params = {"q": query}
        headers = {
            "accept": "text/html,application/xhtml+xml",
            "user-agent": "Mozilla/5.0 local-realtime-search/0.1",
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers, follow_redirects=True) as client:
            response = await client.get("https://html.duckduckgo.com/html/", params=params)
            response.raise_for_status()

        parser = _DdgHtmlParser()
        parser.feed(response.text)
        results: list[SearchResult] = []
        for index, item in enumerate(parser.results[:limit], start=1):
            results.append(
                SearchResult(
                    title=item.get("title", item.get("url", "")),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    provider=self.name,
                    rank=index,
                )
            )
        return [result for result in results if result.url]
