from app.mcp_payload import format_mcp_research_payload


def test_mcp_payload_keeps_direct_answer_and_instruction() -> None:
    payload = format_mcp_research_payload(
        {
            "direct_answer": "Today is 2026-06-02 in Asia/Seoul.",
            "citations": [],
            "sources": [],
            "mode": "fast",
            "requested_mode": "fast",
        }
    )

    assert payload["answer_direct"] == "Today is 2026-06-02 in Asia/Seoul."
    assert "answer_direct" in payload["instruction_to_model"]


def test_mcp_payload_compacts_sources_and_citations() -> None:
    payload = format_mcp_research_payload(
        {
            "direct_answer": None,
            "citations": [
                {
                    "id": 1,
                    "title": "Docs",
                    "url": "https://example.com/docs",
                    "text": "Evidence text",
                    "provider": "searxng",
                    "source_type": "page",
                    "extra": "drop me",
                }
            ],
            "sources": [
                {
                    "title": "Docs",
                    "url": "https://example.com/docs",
                    "snippet": "Snippet",
                    "provider": "searxng",
                    "source_label": "official docs",
                    "score": 10.0,
                    "canonical_url": "https://example.com/docs",
                }
            ],
        }
    )

    assert payload["citations"] == [
        {
            "id": 1,
            "title": "Docs",
            "url": "https://example.com/docs",
            "text": "Evidence text",
            "provider": "searxng",
            "published_or_updated": None,
            "source_type": "page",
        }
    ]
    assert payload["sources"][0]["url"] == "https://example.com/docs"
    assert "canonical_url" not in payload["sources"][0]
