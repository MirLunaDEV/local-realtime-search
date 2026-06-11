from app.config import Settings
from app.modes import get_mode_profile, select_research_mode


def test_fast_profile_is_smaller_than_balanced() -> None:
    settings = Settings()
    fast = get_mode_profile("fast", settings)
    balanced = get_mode_profile("balanced", settings)

    assert fast.effective_mode == "fast"
    assert fast.max_evidence_chars < balanced.max_evidence_chars
    assert fast.lm_studio_max_tokens < balanced.lm_studio_max_tokens
    assert fast.search_timeout_seconds >= 4.0


def test_deep_profile_is_larger_than_balanced() -> None:
    settings = Settings()
    deep = get_mode_profile("deep", settings)
    balanced = get_mode_profile("balanced", settings)

    assert deep.effective_mode == "deep"
    assert deep.max_fetch_urls > balanced.max_fetch_urls
    assert deep.lm_studio_max_tokens > balanced.lm_studio_max_tokens


def test_deepsearch_profile_is_larger_than_deep() -> None:
    settings = Settings()
    deepsearch = get_mode_profile("deepsearch", settings)
    deep = get_mode_profile("deep", settings)

    assert deepsearch.effective_mode == "deepsearch"
    assert deepsearch.max_query_variants > deep.max_query_variants
    assert deepsearch.max_candidate_urls > deep.max_candidate_urls
    assert deepsearch.max_fetch_urls > deep.max_fetch_urls
    assert deepsearch.max_evidence_chars > deep.max_evidence_chars
    assert deepsearch.max_chunks_per_page > deep.max_chunks_per_page
    assert deepsearch.search_result_limit > deep.search_result_limit
    assert deepsearch.mcp_max_citations > deep.mcp_max_citations


def test_deepsearch_aliases_map_to_deepsearch() -> None:
    assert get_mode_profile("deep-search", Settings()).effective_mode == "deepsearch"
    assert get_mode_profile("deep_search", Settings()).effective_mode == "deepsearch"
    assert get_mode_profile("research", Settings()).effective_mode == "deepsearch"


def test_unknown_mode_falls_back_to_fast() -> None:
    profile = get_mode_profile("turbo", Settings())

    assert profile.requested_mode == "turbo"
    assert profile.effective_mode == "fast"


def test_auto_mode_uses_fast_for_direct_answers() -> None:
    selection = select_research_mode(
        "오늘 날짜와 현재 시간이 뭐야?",
        requested_mode="auto",
        requested_freshness=None,
        direct_answer_label="current_datetime",
    )

    assert selection.auto is True
    assert selection.selected_mode == "fast"
    assert selection.reason == "direct_runtime_answer"


def test_auto_mode_uses_fast_for_weather() -> None:
    selection = select_research_mode(
        "What is the weather in Seoul today?",
        requested_mode="auto",
        requested_freshness="day",
    )

    assert selection.selected_mode == "fast"
    assert selection.answer_strategy == "weather"


def test_auto_mode_uses_deepsearch_for_benchmarks() -> None:
    selection = select_research_mode(
        "What are the latest Qwen local reasoning model benchmark results?",
        requested_mode="auto",
        requested_freshness="month",
    )

    assert selection.selected_mode == "deepsearch"
    assert selection.reason == "benchmark_requires_broad_evidence"


def test_auto_mode_uses_deep_for_comparisons() -> None:
    selection = select_research_mode(
        "Compare LM Studio MCP with Open WebUI web search.",
        requested_mode="auto",
        requested_freshness="month",
    )

    assert selection.selected_mode == "deep"
    assert selection.answer_strategy == "comparison"


def test_auto_mode_uses_balanced_for_docs_lookup() -> None:
    selection = select_research_mode(
        "How do you enable JSON search results in SearXNG?",
        requested_mode="auto",
        requested_freshness="year",
    )

    assert selection.selected_mode == "balanced"
    assert selection.answer_strategy == "docs_lookup"


def test_explicit_mode_is_respected() -> None:
    selection = select_research_mode(
        "What are the latest Qwen local reasoning model benchmark results?",
        requested_mode="fast",
        requested_freshness="month",
    )

    assert selection.auto is False
    assert selection.selected_mode == "fast"
    assert selection.reason == "explicit_mode"
