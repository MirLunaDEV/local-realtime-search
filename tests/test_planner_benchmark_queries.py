from app.planner import plan_queries


def test_plan_queries_compacts_long_benchmark_requests() -> None:
    queries = plan_queries(
        "Gemma 4 12B latest benchmark scores MMLU GSM8K HumanEval MATH BBH and "
        "HuggingFace Reddit Twitter Discord GitHub Issues community reviews comparison analysis. "
        "Include Google official announcement, 7B version differences, reasoning, and code generation.",
        max_queries=8,
        freshness="month",
    )

    assert queries[0] == "Gemma 4 12B benchmark"
    assert "Gemma 4 12B Hugging Face" in queries
    assert "site:ai.google.dev Gemma 4 12B" in queries
    assert all(len(query) < 120 for query in queries)
