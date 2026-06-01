from app.provider_health import SearchTrace, summarize_search_traces


def test_summarize_search_traces_reports_provider_statuses() -> None:
    traces = [
        SearchTrace("searxng", "q1", "month", False, 3, 100),
        SearchTrace("searxng", "q2", "month", True, 2, 5),
        SearchTrace("duckduckgo_html", "q1", "month", False, 0, 2500, "timeout"),
        SearchTrace("official_hints", "q1", "month", False, 0, 0),
    ]

    health = {item["provider"]: item for item in summarize_search_traces(traces)}

    assert health["searxng"]["status"] == "ok"
    assert health["searxng"]["cache_hits"] == 1
    assert health["searxng"]["result_count"] == 5
    assert health["duckduckgo_html"]["status"] == "down"
    assert health["official_hints"]["status"] == "empty"
