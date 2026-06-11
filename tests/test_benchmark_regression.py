import json
from pathlib import Path

from scripts.benchmark import compare_reports, evaluate_case_result, filter_cases, summarize


def test_default_benchmark_questions_are_valid_quality_cases() -> None:
    cases = json.loads(Path("benchmarks/questions.json").read_text(encoding="utf-8"))
    ids = [case["id"] for case in cases]
    rendered = json.dumps(cases, ensure_ascii=False)

    assert cases
    assert len(ids) == len(set(ids))
    assert "�" not in rendered
    assert "濡" not in rendered
    assert any(case.get("category") == "direct_answer" for case in cases)
    assert any(case.get("category") == "weather" for case in cases)
    assert any(case.get("category") == "benchmark" for case in cases)
    for case in cases:
        assert isinstance(case.get("id"), str) and case["id"]
        assert isinstance(case.get("question"), str) and case["question"]
        assert isinstance(case.get("expected_domains", []), list)


def test_evaluate_case_result_passes_quality_gates() -> None:
    result = evaluate_case_result(
        {
            "id": "lmstudio_mcp",
            "expected_domains": ["lmstudio.ai"],
            "expected_answer_strategy": "general_research",
            "required_evidence_terms": ["MCP"],
            "allowed_search_backend_statuses": ["ok", "degraded"],
        },
        {
            "answer": "LM Studio supports MCP tools with citations [1].",
            "citations": [
                {
                    "title": "LM Studio MCP docs",
                    "url": "https://lmstudio.ai/docs/mcp",
                    "text": "MCP tools are supported.",
                }
            ],
            "sources": [
                {
                    "title": "LM Studio docs",
                    "url": "https://lmstudio.ai/docs/mcp",
                    "snippet": "MCP tools",
                }
            ],
            "answer_strategy": {"name": "general_research"},
            "search_backend_status": {"status": "degraded"},
            "warnings": [],
        },
        elapsed_ms=1200,
    )

    assert result["ok"] is True
    assert result["failure_reasons"] == []
    assert result["expected_domain_citations"] == 1


def test_filter_cases_selects_ids_categories_and_limits() -> None:
    cases = [
        {"id": "a", "category": "smoke"},
        {"id": "b", "category": "weather"},
        {"id": "c", "category": "weather"},
    ]

    assert filter_cases(cases, case_ids=["a"], categories=[], limit=None) == [cases[0]]
    assert filter_cases(cases, case_ids=[], categories=["weather"], limit=1) == [cases[1]]
    assert filter_cases(cases, case_ids=["c"], categories=["weather"], limit=None) == [cases[2]]


def test_evaluate_case_result_reports_actionable_failures() -> None:
    result = evaluate_case_result(
        {
            "id": "bad_case",
            "expected_domains": ["lmstudio.ai"],
            "expected_answer_strategy": "docs_lookup",
            "required_evidence_terms": ["MCP"],
            "forbidden_answer_terms": ["estimated"],
        },
        {
            "answer": "These are estimated results.",
            "citations": [
                {
                    "title": "Unrelated",
                    "url": "https://example.com/post",
                    "text": "No relevant evidence.",
                }
            ],
            "sources": [],
            "answer_strategy": {"name": "general_research"},
            "search_backend_status": {"status": "ok"},
            "warnings": [],
        },
        elapsed_ms=500,
    )

    assert result["ok"] is False
    assert any("expected_domain_citations" in reason for reason in result["failure_reasons"])
    assert any("forbidden_answer_term" in reason for reason in result["failure_reasons"])
    assert any("answer_strategy" in reason for reason in result["failure_reasons"])


def test_evaluate_case_result_allows_direct_answers_without_citations() -> None:
    result = evaluate_case_result(
        {
            "id": "local_current_datetime",
            "allow_direct_answer": True,
            "min_citations": 0,
            "min_sources": 0,
            "expected_answer_strategy": "current_datetime",
            "allowed_search_backend_statuses": ["not_used"],
        },
        {
            "answer": "The current date and time is 2026-06-12 09:30:00 (Asia/Seoul).",
            "citations": [],
            "sources": [],
            "answer_strategy": {"name": "current_datetime"},
            "search_backend_status": {"status": "not_used"},
            "warnings": [],
        },
        elapsed_ms=5,
    )

    assert result["ok"] is True
    assert result["citation_count"] == 0


def test_summarize_includes_regression_metrics() -> None:
    summary = summarize(
        [
            {
                "ok": True,
                "elapsed_ms": 100,
                "citation_count": 2,
                "expected_domain_citations": 1,
                "expected_domain_required": True,
                "warnings": [],
                "provider_failure_count": 0,
            },
            {
                "ok": False,
                "elapsed_ms": 300,
                "citation_count": 0,
                "expected_domain_citations": 0,
                "expected_domain_required": True,
                "warnings": ["down"],
                "provider_failure_count": 1,
                "id": "failed",
            },
        ]
    )

    assert summary["success_rate"] == 0.5
    assert summary["expected_domain_citation_rate"] == 0.5
    assert summary["avg_citation_count"] == 1
    assert summary["avg_warning_count"] == 0.5
    assert summary["provider_failure_count"] == 1
    assert summary["failed"] == 1
    assert summary["all_passed"] is False
    assert summary["failed_case_ids"] == ["failed"]


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


def test_compare_reports_flags_failed_cases() -> None:
    comparison = compare_reports(
        {"summary": {"failed": 1, "success_rate": 0.9, "expected_domain_citation_rate": 0.9, "p90_ms": 1000}},
        {"summary": {"failed": 0, "success_rate": 0.9, "expected_domain_citation_rate": 0.9, "p90_ms": 1000}},
        max_p90_regression_ms=2000,
        min_success_rate=None,
        min_expected_domain_rate=None,
    )

    assert not comparison["ok"]
    assert comparison["failures"] == ["1 benchmark case(s) failed quality gates"]
