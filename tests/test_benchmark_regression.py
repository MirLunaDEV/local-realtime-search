from scripts.benchmark import compare_reports, summarize


def test_summarize_includes_regression_metrics() -> None:
    summary = summarize(
        [
            {
                "ok": True,
                "elapsed_ms": 100,
                "citation_count": 2,
                "expected_domain_citations": 1,
                "warnings": [],
                "provider_failure_count": 0,
            },
            {
                "ok": False,
                "elapsed_ms": 300,
                "citation_count": 0,
                "expected_domain_citations": 0,
                "warnings": ["down"],
                "provider_failure_count": 1,
            },
        ]
    )

    assert summary["success_rate"] == 0.5
    assert summary["expected_domain_citation_rate"] == 0.5
    assert summary["avg_citation_count"] == 1
    assert summary["avg_warning_count"] == 0.5
    assert summary["provider_failure_count"] == 1


def test_compare_reports_flags_regression() -> None:
    comparison = compare_reports(
        {"summary": {"success_rate": 0.5, "expected_domain_citation_rate": 0.4, "p90_ms": 8000}},
        {"summary": {"success_rate": 1.0, "expected_domain_citation_rate": 0.8, "p90_ms": 1000}},
        max_p90_regression_ms=2000,
        min_success_rate=0.8,
        min_expected_domain_rate=0.7,
    )

    assert not comparison["ok"]
    assert len(comparison["failures"]) == 3
