from app.answer_strategy import classify_answer_strategy


def test_strategy_direct_answer_skips_search() -> None:
    strategy = classify_answer_strategy("오늘 날짜 알려줘", direct_answer_label="current_date")

    assert strategy.name == "current_date"
    assert strategy.use_web_search is False
    assert strategy.must_cite is False


def test_strategy_weather_uses_weather_provider() -> None:
    strategy = classify_answer_strategy("오늘 서울 날씨 알려줘")

    assert strategy.name == "weather"
    assert strategy.use_weather_provider is True
    assert strategy.use_web_search is False
    assert strategy.freshness == "day"


def test_strategy_detects_benchmark() -> None:
    strategy = classify_answer_strategy("latest Qwen 9B benchmark results")

    assert strategy.name == "benchmark"
    assert strategy.freshness == "month"
    assert "github_primary" in strategy.preferred_sources


def test_strategy_detects_korean_benchmark() -> None:
    strategy = classify_answer_strategy("최신 Qwen 9B 벤치마크 결과 알려줘")

    assert strategy.name == "benchmark"
    assert strategy.freshness == "month"


def test_strategy_detects_comparison() -> None:
    strategy = classify_answer_strategy("Compare LM Studio MCP with Open WebUI search")

    assert strategy.name == "comparison"
    assert strategy.must_cite is True


def test_strategy_detects_korean_comparison() -> None:
    strategy = classify_answer_strategy("LM Studio MCP와 Open WebUI 검색을 비교해줘")

    assert strategy.name == "comparison"
    assert strategy.must_cite is True


def test_strategy_detects_docs_lookup() -> None:
    strategy = classify_answer_strategy("LM Studio MCP official docs")

    assert strategy.name == "docs_lookup"
    assert "official" in strategy.preferred_sources


def test_strategy_detects_how_to_docs_lookup() -> None:
    strategy = classify_answer_strategy("How do I use Crawl4AI to extract markdown for LLM context?", requested_freshness="year")

    assert strategy.name == "docs_lookup"
