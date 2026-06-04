import pytest

from app.fetch.fetcher import fetch_page_best_effort
from app.pipeline import _safe_fetch
from app.search.base import SearchResult
from app.security import UnsafeUrlError, assess_url_safety, ensure_url_safe_for_fetch
from app.cache import SearchCache
from app.fetch.http_fetcher import FetchedPage


def test_blocks_unsupported_schemes() -> None:
    result = assess_url_safety("file:///C:/Windows/win.ini")

    assert not result.allowed
    assert "unsupported URL scheme" in str(result.reason)


def test_blocks_localhost_and_private_ips() -> None:
    assert not assess_url_safety("http://localhost:1234").allowed
    assert not assess_url_safety("http://127.0.0.1:1234").allowed
    assert not assess_url_safety("http://192.168.0.1").allowed


def test_blocks_hostnames_that_resolve_to_private_ips() -> None:
    def resolver(host: str, port):
        return [(0, 0, 0, "", ("10.0.0.5", 0))]

    result = assess_url_safety("https://example.test", resolver=resolver)

    assert not result.allowed
    assert "resolves to private" in str(result.reason)


def test_allows_public_url_without_dns_resolution() -> None:
    result = assess_url_safety("https://example.com/docs", resolve_hostnames=False)

    assert result.allowed
    assert result.host == "example.com"


def test_can_opt_into_private_network_fetch() -> None:
    result = ensure_url_safe_for_fetch("http://127.0.0.1:8080", allow_private_network=True)

    assert result.allowed


@pytest.mark.anyio
async def test_fetcher_blocks_unsafe_url_before_network() -> None:
    with pytest.raises(UnsafeUrlError):
        await fetch_page_best_effort("http://127.0.0.1:1234", fetcher="http")


@pytest.mark.anyio
async def test_safe_fetch_reports_blocked_url_without_snippet(tmp_path) -> None:
    result = SearchResult(
        title="Local admin",
        url="http://127.0.0.1:1234/admin",
        snippet="This should not become evidence.",
    )

    _, page, cache_hit, used_fetcher = await _safe_fetch(
        result,
        0.1,
        SearchCache(str(tmp_path / "cache.sqlite3")),
        60,
        "http",
        0.1,
        False,
        True,
    )

    assert page is None
    assert cache_hit is False
    assert used_fetcher == "blocked_url"


@pytest.mark.anyio
async def test_safe_fetch_blocks_unsafe_url_before_cache_lookup(tmp_path) -> None:
    cache = SearchCache(str(tmp_path / "cache.sqlite3"))
    cache.set_page("http://127.0.0.1:1234/admin", FetchedPage("http://127.0.0.1:1234/admin", "Cached", "secret", 200))
    result = SearchResult(title="Local admin", url="http://127.0.0.1:1234/admin")

    _, page, cache_hit, used_fetcher = await _safe_fetch(
        result,
        0.1,
        cache,
        60,
        "http",
        0.1,
        False,
        True,
    )

    assert page is None
    assert cache_hit is False
    assert used_fetcher == "blocked_url"
