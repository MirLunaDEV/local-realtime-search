from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    provider: str = "unknown"
    rank: int = 0
    published_or_updated: str | None = None


class SearchProvider(Protocol):
    name: str

    async def search(self, query: str, *, freshness: str | None = None, limit: int = 10) -> list[SearchResult]:
        ...

