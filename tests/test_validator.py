from app.evidence import EvidenceChunk
from app.knowledge_prior import KnowledgePrior
from app.validator import validate_answer


def test_validate_answer_flags_missing_citation() -> None:
    report = validate_answer("Claim [2]", [EvidenceChunk(1, "Doc", "https://example.com", "Text", "test")], None)

    assert not report.ok
    assert report.missing_citation_ids == [2]


def test_validate_answer_flags_prior_drift() -> None:
    report = validate_answer(
        "Use LM Studio, SearXNG, Crawl4AI, and fastCRW [1].",
        [EvidenceChunk(1, "Doc", "https://docs.searxng.org/dev/search_api.html", "Text", "test")],
        KnowledgePrior("local_lm_studio_search_stack", "Use LM Studio, SearXNG, Crawl4AI."),
    )

    assert report.ok
    assert any(issue.code == "prior_drift_terms" for issue in report.issues)


def test_validate_answer_passes_core_stack() -> None:
    report = validate_answer(
        "Use LM Studio, SearXNG, and Crawl4AI [1].",
        [EvidenceChunk(1, "Doc", "https://docs.searxng.org/dev/search_api.html", "Text", "test")],
        KnowledgePrior("local_lm_studio_search_stack", "Use LM Studio, SearXNG, Crawl4AI."),
    )

    assert report.ok
    assert report.issues == []


def test_validate_answer_flags_searxng_default_format() -> None:
    report = validate_answer(
        "Set default_format: json, then call the endpoint.",
        [EvidenceChunk(1, "Doc", "https://docs.searxng.org/dev/search_api.html", "Text", "test")],
        KnowledgePrior("searxng_json_api", "Use search.formats and format=json."),
    )

    assert report.ok
    assert any(issue.code == "unsupported_searxng_default_format" for issue in report.issues)


def test_validate_answer_flags_cache_scaleout_drift() -> None:
    report = validate_answer(
        "Use Redis and OpenSearch as the main cache [1].",
        [EvidenceChunk(1, "Doc", "https://docs.python.org/3/library/sqlite3.html", "Text", "test")],
        KnowledgePrior("local_search_cache_strategy", "Use SQLite cache by default."),
    )

    assert report.ok
    assert any(issue.code == "cache_required_terms_missing" for issue in report.issues)
    assert any(issue.code == "cache_scaleout_terms" for issue in report.issues)


def test_validate_answer_passes_cache_strategy() -> None:
    report = validate_answer(
        "Use a SQLite cache for search results and fetched pages, with separate TTLs [1].",
        [EvidenceChunk(1, "Doc", "https://docs.python.org/3/library/sqlite3.html", "Text", "test")],
        KnowledgePrior("local_search_cache_strategy", "Use SQLite cache by default."),
    )

    assert report.ok
    assert report.issues == []


def test_validate_answer_flags_citation_quality_gaps() -> None:
    report = validate_answer(
        "Validate sources before answering [1].",
        [EvidenceChunk(1, "Doc", "https://docs.searxng.org/dev/search_api.html", "Text", "test")],
        KnowledgePrior("local_citation_quality", "Validate citation IDs and weak sources."),
    )

    assert report.ok
    assert any(issue.code == "citation_quality_required_terms_missing" for issue in report.issues)
