from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx


@dataclass(frozen=True)
class FetchedPage:
    url: str
    title: str
    text: str
    status_code: int


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._title_depth = 0
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "title":
            self._title_depth += 1
        if tag in {"p", "br", "li", "h1", "h2", "h3", "article", "section"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title" and self._title_depth:
            self._title_depth -= 1
        if tag in {"p", "li", "h1", "h2", "h3"}:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        stripped = data.strip()
        if not stripped:
            return
        if self._title_depth:
            self.title_parts.append(stripped)
        self.text_parts.append(stripped)


def extract_text(html: str) -> tuple[str, str]:
    parser = _TextExtractor()
    parser.feed(html)
    title = " ".join(parser.title_parts).strip()
    text = " ".join(parser.text_parts)
    text = re.sub(r"\s+", " ", text).strip()
    return title, text


async def fetch_page(url: str, timeout_seconds: float = 3.0) -> FetchedPage:
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "user-agent": "local-realtime-search/0.1 (+https://localhost)",
    }
    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
    title, text = extract_text(response.text)
    return FetchedPage(url=str(response.url), title=title, text=text, status_code=response.status_code)

