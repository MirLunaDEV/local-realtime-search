from app.cache import SearchCache
from app.fetch.http_fetcher import FetchedPage
from app.search.base import SearchResult


def test_search_cache_roundtrip(tmp_path) -> None:
    cache = SearchCache(str(tmp_path / "cache.sqlite3"))
    results = [SearchResult(title="Title", url="https://example.com", snippet="Snippet", provider="test", rank=1)]

    cache.set_search("key", results)
    cached = cache.get_search("key", ttl_seconds=60)

    assert cached == results


def test_page_cache_roundtrip(tmp_path) -> None:
    cache = SearchCache(str(tmp_path / "cache.sqlite3"))
    page = FetchedPage(url="https://example.com", title="Title", text="Text", status_code=200)

    cache.set_page(page.url, page)
    cached = cache.get_page(page.url, ttl_seconds=60)

    assert cached == page
