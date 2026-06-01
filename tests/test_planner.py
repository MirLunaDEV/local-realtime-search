from app.planner import plan_queries


def test_plan_queries_includes_current_variants() -> None:
    queries = plan_queries("latest LM Studio tool use", max_queries=6, freshness="month")

    assert queries[0] == "latest LM Studio tool use"
    assert any("news" in query for query in queries)
    assert any("official documentation" in query for query in queries)


def test_plan_queries_prioritizes_lm_studio_tool_docs() -> None:
    queries = plan_queries("How does LM Studio support tool use?", max_queries=6, freshness="month")

    assert "site:lmstudio.ai/docs LM Studio tool use" in queries
    assert "site:lmstudio.ai/docs LM Studio OpenAI compatible tools" in queries


def test_plan_queries_prioritizes_local_search_stack_components() -> None:
    queries = plan_queries("What is the best free local-first web search stack to use with LM Studio?", max_queries=8)

    joined = "\n".join(queries)
    assert "SearXNG Crawl4AI LM Studio local web search stack" in joined
    assert "site:docs.searxng.org" in joined
    assert "site:docs.crawl4ai.com" in joined


def test_plan_queries_prioritizes_korean_local_search_stack_components() -> None:
    queries = plan_queries(
        "\ub85c\uceec LLM\uc5d0\uc11c \uc2e4\uc2dc\uac04 \uc6f9\uac80\uc0c9\uc744 "
        "\ubb34\ub8cc\ub85c \ubd99\uc774\ub294 \uac00\uc7a5 \uc88b\uc740 \ubc29\ubc95\uc740?",
        max_queries=8,
    )

    joined = "\n".join(queries)
    assert "SearXNG Crawl4AI LM Studio local web search stack" in joined
    assert "site:docs.searxng.org" in joined
    assert "site:docs.crawl4ai.com" in joined


def test_plan_queries_prioritizes_cache_strategy_sources() -> None:
    queries = plan_queries(
        "What cache strategy should a local realtime search assistant use for search results and fetched pages?",
        max_queries=8,
    )

    joined = "\n".join(queries)
    assert "SQLite cache strategy" in joined
    assert "site:docs.searxng.org" in joined


def test_plan_queries_prioritizes_citation_quality_sources() -> None:
    queries = plan_queries(
        "How should a web-grounded local LLM assistant validate citations and weak sources?",
        max_queries=8,
    )

    joined = "\n".join(queries)
    assert "citation validation" in joined
    assert "site:docs.searxng.org" in joined


def test_plan_queries_adds_korean_and_english_variants() -> None:
    queries = plan_queries("LM Studio 최신 검색", max_queries=6, freshness="month")

    assert any("최신" in query for query in queries)
    assert any("release notes" in query for query in queries)
