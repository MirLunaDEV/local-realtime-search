import pytest

from app.search.official_hints import OfficialHintsProvider


@pytest.mark.anyio
async def test_official_hints_adds_lm_studio_tool_docs() -> None:
    results = await OfficialHintsProvider().search("LM Studio tool use")

    assert results
    assert results[0].url == "https://lmstudio.ai/docs/developer/openai-compat/tools"


@pytest.mark.anyio
async def test_official_hints_adds_local_search_stack_sources() -> None:
    results = await OfficialHintsProvider().search("free local search stack with LM Studio")
    urls = {result.url for result in results}

    assert "https://docs.searxng.org/dev/search_api.html" in urls
    assert "https://github.com/unclecode/crawl4ai" in urls
    assert "https://lmstudio.ai/docs/api/" in urls


@pytest.mark.anyio
async def test_official_hints_adds_searxng_json_docs() -> None:
    results = await OfficialHintsProvider().search("enable SearXNG JSON API")
    urls = {result.url for result in results}

    assert "https://docs.searxng.org/dev/search_api.html" in urls
    assert "https://docs.searxng.org/admin/settings/settings.html" in urls


@pytest.mark.anyio
async def test_official_hints_adds_cache_strategy_sources() -> None:
    results = await OfficialHintsProvider().search("cache strategy for search results and fetched pages")
    urls = {result.url for result in results}

    assert "https://docs.searxng.org/dev/search_api.html" in urls
    assert "https://docs.python.org/3/library/sqlite3.html" in urls


@pytest.mark.anyio
async def test_official_hints_adds_citation_quality_sources() -> None:
    results = await OfficialHintsProvider().search("validate citations and weak sources")
    urls = {result.url for result in results}

    assert "https://docs.searxng.org/dev/search_api.html" in urls
    assert "https://github.com/unclecode/crawl4ai" in urls
