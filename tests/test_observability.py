import json

from app.observability import logger, log_research_result


def test_log_research_result_emits_json(monkeypatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(logger, "info", messages.append)

    log_research_result(
        "ask",
        {
            "request_id": "abc123",
            "answer_strategy": {"name": "weather"},
            "mode": "fast",
            "freshness": "day",
            "citations": [{"id": 1}],
            "sources": [{"url": "https://example.com"}],
            "warnings": ["thin"],
            "search_backend_status": {"status": "not_used"},
            "weather_provider_status": {"status": "ok"},
            "timings_ms": {"total": 42},
        },
    )

    payload = json.loads(messages[-1])
    assert payload["request_id"] == "abc123"
    assert payload["strategy"] == "weather"
    assert payload["total_ms"] == 42
