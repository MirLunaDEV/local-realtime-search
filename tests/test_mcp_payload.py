from app.mcp_payload import format_mcp_research_payload


def test_mcp_payload_keeps_direct_answer_and_instruction() -> None:
    payload = format_mcp_research_payload(
        {
            "direct_answer": "Today is 2026-06-02 in Asia/Seoul.",
            "citations": [],
            "sources": [],
            "mode": "fast",
            "requested_mode": "fast",
            "adaptive_mode": {"auto": False, "selected_mode": "fast", "reason": "explicit_mode"},
            "weather_provider_status": {"status": "not_used"},
            "answer_strategy": {"name": "current_date", "guidance": "direct"},
        }
    )

    assert payload["answer_direct"] == "Today is 2026-06-02 in Asia/Seoul."
    assert "answer_direct" in payload["instruction_to_model"]
    assert payload["next_action"] == "write_final_answer"
    assert payload["ready_to_answer"] is True
    assert payload["synthesis_contract"]["write_final_answer_now"] is True
    assert payload["adaptive_mode"]["selected_mode"] == "fast"
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
    assert payload["evidence_status"]["ready_to_answer"] is True


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


def test_mcp_payload_returns_terminal_direct_answer_without_citations() -> None:
    payload = format_mcp_research_payload(
        {
            "direct_answer": None,
            "citations": [],
            "sources": [],
            "warnings": ["SearXNG search backend is empty at http://127.0.0.1:8080."],
            "search_backend_status": {"status": "empty"},
        }
    )

    assert payload["terminal_result"] is True
    assert payload["citations_empty"] is True
    assert payload["evidence_status"]["status"] == "empty"
    assert payload["evidence_status"]["ready_to_answer"] is True
    assert payload["tool_call_policy"]["call_again_for_same_question"] is False
    assert payload["answer_direct"]
    assert "Do not call local_research again" in payload["answer_direct"]
    assert "Do not provide estimated benchmark scores" in payload["answer_direct"]


def test_mcp_payload_does_not_treat_empty_backend_as_failure_when_citations_exist() -> None:
    payload = format_mcp_research_payload(
        {
            "direct_answer": None,
            "citations": [
                {
                    "id": 1,
                    "title": "Model card",
                    "url": "https://huggingface.co/example/model",
                    "text": "The model card includes benchmark notes.",
                    "provider": "huggingface_models",
                    "source_type": "page",
                },
                {
                    "id": 2,
                    "title": "GitHub repo",
                    "url": "https://github.com/example/repo",
                    "text": "The repository includes evaluation scripts.",
                    "provider": "github_repositories",
                    "source_type": "page",
                },
            ],
            "sources": [
                {
                    "title": "Model card",
                    "url": "https://huggingface.co/example/model",
                    "snippet": "Benchmark notes",
                    "provider": "huggingface_models",
                    "source_label": "official docs",
                }
            ],
            "search_backend_status": {"status": "empty"},
            "warnings": ["SearXNG search backend is empty at http://127.0.0.1:8080; using fallback sources only."],
        }
    )

    assert payload["citations_empty"] is False
    assert payload["evidence_status"]["status"] == "partial"
    assert payload["evidence_status"]["search_backend_status"] == "empty"
    assert payload["evidence_status"]["search_backend_required_for_success"] is False
    assert "do not say the whole research failed" in payload["instruction_to_model"]
    assert "when citations exist" in payload["synthesis_contract"]["empty_backend_policy"]
