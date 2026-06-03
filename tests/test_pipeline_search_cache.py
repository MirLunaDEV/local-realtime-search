from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.cache import SearchCache
from app.pipeline import _safe_search
from app.search.base import SearchResult


@dataclass
class CountingProvider:
    name: str = "counting"
    calls: int = 0

    async def search(self, query: str, *, freshness: str | None = None, limit: int = 10) -> list[SearchResult]:
        self.calls += 1
        return [SearchResult(title="Fresh", url="https://example.com/fresh", snippet=query, provider=self.name)]


@pytest.mark.anyio
async def test_safe_search_ignores_empty_cache(tmp_path) -> None:
    cache = SearchCache(str(tmp_path / "cache.sqlite3"))
    cache.set_search("counting|month|query", [])
    provider = CountingProvider()

    results, trace = await _safe_search(provider, "query", "month", cache, ttl_seconds=60)

    assert provider.calls == 1
    assert trace.cache_hit is False
    assert results[0].title == "Fresh"
