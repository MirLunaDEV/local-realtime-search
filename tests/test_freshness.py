from app.freshness import infer_freshness


def test_infer_freshness_preserves_explicit_value() -> None:
    assert infer_freshness("old release notes", "year") == "year"


def test_infer_freshness_detects_today_weather() -> None:
    assert infer_freshness("오늘 서울 날씨 알려줘", None) == "day"
    assert infer_freshness("What is the weather right now?", None) == "day"


def test_infer_freshness_detects_recent_updates() -> None:
    assert infer_freshness("latest LM Studio MCP changes", None) == "month"
    assert infer_freshness("최신 Qwen 벤치마크 알려줘", None) == "month"
