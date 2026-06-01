from app.knowledge_prior import get_knowledge_prior


def test_local_search_stack_prior() -> None:
    prior = get_knowledge_prior("What is the best free local-first web search stack to use with LM Studio?")

    assert prior is not None
    assert "SearXNG" in prior.text
    assert "Crawl4AI" in prior.text
    assert "SQLite cache" in prior.text


def test_korean_local_search_stack_prior() -> None:
    prior = get_knowledge_prior(
        "\ub85c\uceec LLM\uc5d0\uc11c \uc2e4\uc2dc\uac04 \uc6f9\uac80\uc0c9\uc744 "
        "\ubb34\ub8cc\ub85c \ubd99\uc774\ub294 \uac00\uc7a5 \uc88b\uc740 \ubc29\ubc95\uc740?"
    )

    assert prior is not None
    assert prior.label == "local_lm_studio_search_stack"
    assert "SearXNG" in prior.text


def test_searxng_json_prior() -> None:
    prior = get_knowledge_prior("How do you enable JSON search results in SearXNG?")

    assert prior is not None
    assert prior.label == "searxng_json_api"
    assert "format=json" in prior.text
    assert "search.formats" in prior.text


def test_cache_strategy_prior() -> None:
    prior = get_knowledge_prior(
        "What cache strategy should a local realtime search assistant use for search results and fetched pages?"
    )

    assert prior is not None
    assert prior.label == "local_search_cache_strategy"
    assert "SQLite cache" in prior.text
    assert "external cache services" in prior.text


def test_citation_quality_prior() -> None:
    prior = get_knowledge_prior("How should a web-grounded local LLM assistant validate citations and weak sources?")

    assert prior is not None
    assert prior.label == "local_citation_quality"
    assert "weak social/video" in prior.text
    assert "citation IDs" in prior.text
