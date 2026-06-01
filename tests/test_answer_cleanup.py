from app.answer_cleanup import cleanup_answer_for_prior
from app.knowledge_prior import KnowledgePrior


def test_cleanup_removes_cache_scaleout_lines_for_default_cache_question() -> None:
    answer = (
        "Use SQLite for the local cache.\n"
        "- Store search results with a short TTL.\n"
        "- If the architecture scales later, Redis or Valkey can be optional.\n"
        "Keep fetched pages in a separate table."
    )

    cleaned = cleanup_answer_for_prior(
        answer,
        "What cache strategy should a local realtime search assistant use?",
        KnowledgePrior("local_search_cache_strategy", "Use SQLite cache by default."),
    )

    assert "SQLite" in cleaned
    assert "Redis" not in cleaned
    assert "Valkey" not in cleaned
    assert "fetched pages" in cleaned


def test_cleanup_keeps_scaleout_terms_when_user_asks_for_scaleout() -> None:
    answer = "Use SQLite locally, then Redis when scale-out is required."

    cleaned = cleanup_answer_for_prior(
        answer,
        "How should this cache strategy scale out with Redis?",
        KnowledgePrior("local_search_cache_strategy", "Use SQLite cache by default."),
    )

    assert "Redis" in cleaned
