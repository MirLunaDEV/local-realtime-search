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
    last_limit: int = 0

    async def search(self, query: str, *, freshness: str | None = None, limit: int = 10) -> list[SearchResult]:
        self.calls += 1
        self.last_limit = limit
        return [SearchResult(title="Fresh", url="https://example.com/fresh", snippet=query, provider=self.name)]


@dataclass
class EmptyThenFreshProvider:
    name: str = "empty_then_fresh"
    calls: int = 0
    freshness_values: list[str | None] | None = None

    def __post_init__(self) -> None:
        if self.freshness_values is None:
            self.freshness_values = []

    async def search(self, query: str, *, freshness: str | None = None, limit: int = 10) -> list[SearchResult]:
        self.calls += 1
        assert self.freshness_values is not None
        self.freshness_values.append(freshness)
        if freshness:
            return []
        return [SearchResult(title="Broadened", url="https://example.com/broadened", snippet=query, provider=self.name)]


@pytest.mark.anyio
async def test_safe_search_ignores_empty_cache(tmp_path) -> None:
    cache = SearchCache(str(tmp_path / "cache.sqlite3"))
    cache.set_search("counting|limit=10|month|query", [])
    provider = CountingProvider()

    results, trace = await _safe_search(provider, "query", "month", cache, ttl_seconds=60, result_limit=10)

    assert provider.calls == 1
    assert provider.last_limit == 10
    assert trace.cache_hit is False
    assert results[0].title == "Fresh"


@pytest.mark.anyio
async def test_safe_search_passes_result_limit_to_provider(tmp_path) -> None:
    cache = SearchCache(str(tmp_path / "cache.sqlite3"))
    provider = CountingProvider()

    await _safe_search(provider, "query", "month", cache, ttl_seconds=60, result_limit=20)

    assert provider.last_limit == 20


@pytest.mark.anyio
async def test_safe_search_broadens_when_freshness_returns_empty(tmp_path) -> None:
    cache = SearchCache(str(tmp_path / "cache.sqlite3"))
    provider = EmptyThenFreshProvider()

    results, trace = await _safe_search(provider, "query", "month", cache, ttl_seconds=60, result_limit=10)

    assert provider.calls == 2
    assert provider.freshness_values == ["month", None]
    assert trace.result_count == 1
    assert results[0].title == "Broadened"
