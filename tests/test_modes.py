from app.config import Settings
from app.modes import get_mode_profile


def test_fast_profile_is_smaller_than_balanced() -> None:
    settings = Settings()
    fast = get_mode_profile("fast", settings)
    balanced = get_mode_profile("balanced", settings)

    assert fast.effective_mode == "fast"
    assert fast.max_evidence_chars < balanced.max_evidence_chars
    assert fast.lm_studio_max_tokens < balanced.lm_studio_max_tokens


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
