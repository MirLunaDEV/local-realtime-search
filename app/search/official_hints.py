from __future__ import annotations

from app.search.base import SearchResult


class OfficialHintsProvider:
    name = "official_hints"

    async def search(self, query: str, *, freshness: str | None = None, limit: int = 10) -> list[SearchResult]:
        lowered = query.lower()
        results: list[SearchResult] = []
        if "lm studio" in lowered and "tool" in lowered:
            results.extend(
                [
                    SearchResult(
                        title="Tool Use - LM Studio OpenAI Compatibility Docs",
                        url="https://lmstudio.ai/docs/developer/openai-compat/tools",
                        snippet=(
                            "LM Studio documents tool use for OpenAI-compatible chat completions, "
                            "including how local models can request tool calls and how clients return tool results."
                        ),
                        provider=self.name,
                        rank=1,
                    ),
                    SearchResult(
                        title="Tool Use | LM Studio App API Docs",
                        url="https://www.lmstudio.ai/docs/app/api/tools",
                        snippet=(
                            "LM Studio's app/API documentation describes tool use support and related local API behavior."
                        ),
                        provider=self.name,
                        rank=2,
                    ),
                    SearchResult(
                        title="Autonomous Agents and Tool Use - LM Studio SDK Docs",
                        url="https://deepwiki.com/lmstudio-ai/docs/4.3-autonomous-agents-and-tool-use",
                        snippet=(
                            "LM Studio SDK docs cover autonomous agents and tool use through SDK orchestration APIs."
                        ),
                        provider=self.name,
                        rank=3,
                    ),
                ]
            )
        if "lm studio" in lowered and "search" in lowered and ("local" in lowered or "free" in lowered):
            results.extend(
                [
                    SearchResult(
                        title="SearXNG Search API - JSON results",
                        url="https://docs.searxng.org/dev/search_api.html",
                        snippet=(
                            "SearXNG provides a search API where clients can request JSON search results "
                            "using format=json, making it suitable as a free self-hosted search backend."
                        ),
                        provider=self.name,
                        rank=1,
                    ),
                    SearchResult(
                        title="SearXNG Documentation",
                        url="https://docs.searxng.org/index.html",
                        snippet=(
                            "SearXNG is a free metasearch engine that can be self-hosted and configured "
                            "for private local-first search workflows."
                        ),
                        provider=self.name,
                        rank=2,
                    ),
                    SearchResult(
                        title="Crawl4AI GitHub",
                        url="https://github.com/unclecode/crawl4ai",
                        snippet=(
                            "Crawl4AI is an open-source LLM-friendly web crawler and scraper for turning "
                            "web pages into usable LLM context."
                        ),
                        provider=self.name,
                        rank=3,
                    ),
                    SearchResult(
                        title="Crawl4AI Complete SDK Documentation",
                        url="https://docs.crawl4ai.com/complete-sdk-reference/",
                        snippet=(
                            "Crawl4AI documentation covers markdown generation, crawler configuration, "
                            "and extraction strategies for LLM context."
                        ),
                        provider=self.name,
                        rank=4,
                    ),
                    SearchResult(
                        title="LM Studio Developer API Docs",
                        url="https://lmstudio.ai/docs/api/",
                        snippet=(
                            "LM Studio provides local APIs and OpenAI-compatible endpoints for connecting "
                            "local models to applications."
                        ),
                        provider=self.name,
                        rank=5,
                    ),
                ]
            )
        if "searxng" in lowered and "json" in lowered:
            results.extend(
                [
                    SearchResult(
                        title="SearXNG Search API - JSON format",
                        url="https://docs.searxng.org/dev/search_api.html",
                        snippet=(
                            "SearXNG search API supports requesting JSON output with format=json "
                            "when JSON is enabled in the instance configuration."
                        ),
                        provider=self.name,
                        rank=1,
                    ),
                    SearchResult(
                        title="SearXNG Settings - search.formats",
                        url="https://docs.searxng.org/admin/settings/settings.html",
                        snippet=(
                            "SearXNG settings.yml can allow response formats under search.formats, "
                            "including html and json."
                        ),
                        provider=self.name,
                        rank=2,
                    ),
                ]
            )
        if "cache" in lowered and ("search" in lowered or "fetched" in lowered or "page" in lowered):
            results.extend(
                [
                    SearchResult(
                        title="SearXNG Search API - results for local caching",
                        url="https://docs.searxng.org/dev/search_api.html",
                        snippet=(
                            "SearXNG search API responses provide the result URLs, titles, snippets, "
                            "engines, and metadata that a local assistant can cache by provider, query, "
                            "freshness, and timestamp."
                        ),
                        provider=self.name,
                        rank=1,
                    ),
                    SearchResult(
                        title="SearXNG Settings - formats and local instance behavior",
                        url="https://docs.searxng.org/admin/settings/settings.html",
                        snippet=(
                            "SearXNG settings documentation describes instance-level behavior such as "
                            "enabled response formats, useful when caching search API output locally."
                        ),
                        provider=self.name,
                        rank=2,
                    ),
                    SearchResult(
                        title="Python sqlite3 - local SQLite cache storage",
                        url="https://docs.python.org/3/library/sqlite3.html",
                        snippet=(
                            "Python's sqlite3 module provides a lightweight local SQL database suitable "
                            "for simple persistent caches without a separate service."
                        ),
                        provider=self.name,
                        rank=3,
                    ),
                    SearchResult(
                        title="LM Studio Developer API Docs",
                        url="https://lmstudio.ai/docs/api/",
                        snippet=(
                            "LM Studio provides local APIs and OpenAI-compatible endpoints that can consume "
                            "cached search/page evidence inside a local assistant."
                        ),
                        provider=self.name,
                        rank=4,
                    ),
                ]
            )
        if "citation" in lowered and ("validate" in lowered or "quality" in lowered or "weak" in lowered):
            results.extend(
                [
                    SearchResult(
                        title="SearXNG Search API - source URLs and metadata",
                        url="https://docs.searxng.org/dev/search_api.html",
                        snippet=(
                            "SearXNG search API results include source URLs, titles, snippets, and engine "
                            "metadata that can be mapped to citation IDs in a web-grounded assistant."
                        ),
                        provider=self.name,
                        rank=1,
                    ),
                    SearchResult(
                        title="Crawl4AI Complete SDK Documentation - markdown extraction",
                        url="https://docs.crawl4ai.com/complete-sdk-reference/",
                        snippet=(
                            "Crawl4AI can extract cleaner page text and markdown for LLM context, improving "
                            "the evidence used behind citations."
                        ),
                        provider=self.name,
                        rank=2,
                    ),
                    SearchResult(
                        title="Crawl4AI GitHub",
                        url="https://github.com/unclecode/crawl4ai",
                        snippet=(
                            "Crawl4AI is an open-source crawler for collecting LLM-friendly evidence from web pages."
                        ),
                        provider=self.name,
                        rank=3,
                    ),
                    SearchResult(
                        title="LM Studio Tool Use Docs - local API evidence flow",
                        url="https://lmstudio.ai/docs/developer/openai-compat/tools",
                        snippet=(
                            "LM Studio's OpenAI-compatible tool-use flow can be used to collect external evidence "
                            "and return tool results before final answer synthesis."
                        ),
                        provider=self.name,
                        rank=4,
                    ),
                ]
            )
        return results[:limit]
