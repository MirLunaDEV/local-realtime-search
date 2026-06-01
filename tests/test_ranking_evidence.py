from app.evidence import chunk_text
from app.ranking import canonicalize_url, rank_results
from app.search.base import SearchResult


def test_canonicalize_url_removes_tracking_params() -> None:
    url = "HTTPS://Example.com/path/?utm_source=x&b=2#section"

    assert canonicalize_url(url) == "https://example.com/path?b=2"


def test_rank_results_deduplicates_and_prefers_relevant_result() -> None:
    results = [
        SearchResult(title="Random", url="https://example.com/a?utm_source=x", snippet="nothing", rank=1),
        SearchResult(title="LM Studio Tool Use", url="https://example.com/a", snippet="tool calling docs", rank=2),
    ]

    ranked = rank_results(results, "LM Studio tool use", limit=10)

    assert len(ranked) == 1
    assert ranked[0].result.title == "LM Studio Tool Use"


def test_chunk_text_overlaps_long_text() -> None:
    chunks = chunk_text("a" * 1000 + " " + "b" * 1000, chunk_chars=900, overlap_chars=100)

    assert len(chunks) == 3
    assert chunks[0].endswith("a" * 100)
