from app.ranking import rank_results
from app.search.base import SearchResult


def test_local_search_stack_ranking_prefers_crawl4ai_over_mcp_directory() -> None:
    results = [
        SearchResult(
            title="SearXNG MCP Server for LM Studio",
            url="https://lobehub.com/mcp/pascalrjt-searxng-websearch-mcp",
            snippet="MCP server for LM Studio search.",
            provider="test",
            rank=1,
        ),
        SearchResult(
            title="Crawl4AI GitHub",
            url="https://github.com/unclecode/crawl4ai",
            snippet="Open-source LLM friendly web crawler that produces markdown context.",
            provider="test",
            rank=3,
        ),
    ]

    ranked = rank_results(results, "What is the best free local-first web search stack to use with LM Studio?")

    assert ranked[0].result.url == "https://github.com/unclecode/crawl4ai"


def test_cache_strategy_ranking_prefers_sqlite_over_scaleout_defaults() -> None:
    results = [
        SearchResult(
            title="OpenSearch cache architecture",
            url="https://example.com/opensearch-cache",
            snippet="Use OpenSearch and Redis for every search cache.",
            provider="test",
            rank=1,
        ),
        SearchResult(
            title="Python sqlite3 local cache",
            url="https://docs.python.org/3/library/sqlite3.html",
            snippet="SQLite is a lightweight local SQL database suitable for persistent local cache data.",
            provider="test",
            rank=3,
        ),
    ]

    ranked = rank_results(
        results,
        "What cache strategy should a local realtime search assistant use for search results and fetched pages?",
    )

    assert ranked[0].result.url == "https://docs.python.org/3/library/sqlite3.html"


def test_citation_quality_ranking_prefers_primary_evidence_sources() -> None:
    results = [
        SearchResult(
            title="Generic citation quality blog",
            url="https://example.com/blog/citation-quality",
            snippet="A generic blog about citation quality.",
            provider="test",
            rank=1,
        ),
        SearchResult(
            title="SearXNG Search API - source URLs and metadata",
            url="https://docs.searxng.org/dev/search_api.html",
            snippet="Search results include URLs, titles, snippets, and source metadata for evidence.",
            provider="test",
            rank=3,
        ),
    ]

    ranked = rank_results(results, "How should a web-grounded local LLM assistant validate citations and weak sources?")

    assert ranked[0].result.url == "https://docs.searxng.org/dev/search_api.html"
