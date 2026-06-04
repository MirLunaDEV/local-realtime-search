from scripts import mcp_server


def test_question_fingerprint_ignores_repeated_research_noise() -> None:
    first = mcp_server._question_fingerprint("2026년 6월 현재 생성형 AI 주요 동향과 성능 비교 분석 latest news")
    second = mcp_server._question_fingerprint(
        "2026년 6월 현재 생성형 AI 주요 동향과 성능 비교 분석 summary brief overview analysis"
    )

    assert first == second


def test_recent_payload_marks_duplicate_tool_call() -> None:
    key = mcp_server._recent_key("same question latest news", "fast", "day")
    mcp_server._RECENT_RESULTS.clear()
    mcp_server._RECENT_RESULTS[key] = (
        10**12,
        {
            "warnings": [],
            "answer_direct": "No evidence.",
            "tool_call_policy": {"call_again_for_same_question": False},
        },
    )

    payload = mcp_server._get_recent_payload(key)

    assert payload is not None
    assert payload["duplicate_tool_call"] is True
    assert "near-duplicate" in payload["warnings"][0]
