from app.mcp_payload import format_mcp_research_payload


def test_mcp_payload_keeps_direct_answer_and_instruction() -> None:
    payload = format_mcp_research_payload(
        {
            "direct_answer": "Today is 2026-06-02 in Asia/Seoul.",
            "citations": [],
            "sources": [],
            "mode": "fast",
            "requested_mode": "fast",
            "weather_provider_status": {"status": "not_used"},
            "answer_strategy": {"name": "current_date", "guidance": "direct"},
        }
    )

    assert payload["answer_direct"] == "Today is 2026-06-02 in Asia/Seoul."
    assert "answer_direct" in payload["instruction_to_model"]
    assert payload["answer_strategy"]["name"] == "current_date"
    assert payload["weather_provider_status"]["status"] == "not_used"


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
    assert payload["source_summary"]["source_label_counts"] == {"official docs": 1}


def test_mcp_payload_uses_deepsearch_budget() -> None:
    citations = [
        {
            "id": index,
            "title": f"Source {index}",
            "url": f"https://example.com/{index}",
            "text": "x" * 1800,
            "provider": "searxng",
            "source_type": "page",
        }
        for index in range(1, 30)
    ]
    payload = format_mcp_research_payload(
        {
            "direct_answer": None,
            "mode": "deepsearch",
            "citations": citations,
            "sources": [],
            "mode_profile": {
                "mcp_max_citations": 24,
                "mcp_max_sources": 24,
                "mcp_citation_text_chars": 1500,
                "mcp_source_snippet_chars": 500,
            },
        }
    )

    assert len(payload["citations"]) == 24
    assert len(payload["citations"][0]["text"]) == 1500
    assert payload["payload_budget"]["max_citations"] == 24
