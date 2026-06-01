from app.evidence import EvidenceChunk
from app.knowledge_prior import KnowledgePrior
from app.prompts import build_finalizer_messages


def test_finalizer_prompt_demands_final_answer_only() -> None:
    messages = build_finalizer_messages(
        "What changed?",
        [EvidenceChunk(id=1, title="Doc", url="https://example.com", text="Evidence", provider="test")],
    )

    combined = "\n".join(message["content"] for message in messages)
    assert "final answer only" in combined.lower()
    assert "No hidden reasoning" in combined


def test_answer_prompt_includes_knowledge_prior() -> None:
    from app.prompts import build_answer_messages

    messages = build_answer_messages(
        "Question",
        [EvidenceChunk(id=1, title="Doc", url="https://example.com", text="Evidence", provider="test")],
        KnowledgePrior(label="prior", text="Use SearXNG and Crawl4AI."),
        "Answer briefly.",
    )

    combined = "\n".join(message["content"] for message in messages)
    assert "Project prior" in combined
    assert "SearXNG and Crawl4AI" in combined
    assert "Answer briefly" in combined


def test_answer_prompt_includes_cache_strategy_rules() -> None:
    from app.prompts import build_answer_messages

    messages = build_answer_messages(
        "Cache strategy?",
        [EvidenceChunk(id=1, title="Doc", url="https://example.com", text="Evidence", provider="test")],
        KnowledgePrior(label="local_search_cache_strategy", text="Use SQLite cache."),
    )

    combined = "\n".join(message["content"] for message in messages)
    assert "Prior-specific output rules" in combined
    assert "local SQLite design" in combined
    assert "scale-out options" in combined
    assert "Forbidden terms" in combined
