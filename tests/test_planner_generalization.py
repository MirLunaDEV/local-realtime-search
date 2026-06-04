from app.planner import plan_queries


def test_plan_queries_compacts_troubleshooting_requests() -> None:
    queries = plan_queries(
        "Please investigate in detail how to fix ModuleNotFoundError: No module named app "
        "in LM Studio MCP server logs, include GitHub issues and docs.",
        max_queries=8,
    )

    assert queries[0] == "ModuleNotFoundError No module named app LM Studio MCP server logs GitHub issues docs"
    assert "ModuleNotFoundError No module named app LM Studio MCP server logs GitHub issues docs error fix" in queries
    assert any("GitHub issue" in query for query in queries)
    assert all(len(query) < 120 for query in queries)


def test_plan_queries_compacts_long_korean_comparison_requests() -> None:
    queries = plan_queries(
        "2026년 6월 현재 Open WebUI와 LM Studio MCP 검색 연동 방식 차이를 상세히 비교 분석해줘. "
        "공식 문서와 GitHub 이슈, 커뮤니티 후기를 포함하여 최신 데이터를 수집해줘.",
        max_queries=8,
        freshness="month",
    )

    assert all("상세히" not in query for query in queries)
    assert all("분석해줘" not in query for query in queries)
    assert any("comparison" in query or "alternatives" in query for query in queries)
    assert any("official documentation" in query for query in queries)
    assert all(len(query) < 120 for query in queries)


def test_plan_queries_adds_community_variants_generically() -> None:
    queries = plan_queries(
        "Find user reviews and Discord community discussion for Open WebUI local search reliability",
        max_queries=8,
    )

    assert any("Reddit review" in query for query in queries)
    assert any("GitHub issues" in query for query in queries)
    assert any("community discussion" in query for query in queries)
