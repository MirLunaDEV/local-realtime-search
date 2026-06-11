from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS = ROOT / "benchmarks" / "questions.json"


def domain_matches(url: str, expected_domains: list[str]) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == domain or host.endswith("." + domain) for domain in expected_domains)


def _items(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _string_groups(value: object) -> list[list[str]]:
    groups: list[list[str]] = []
    if not isinstance(value, list):
        return groups
    for item in value:
        if isinstance(item, list):
            group = [str(part) for part in item if str(part).strip()]
        else:
            group = [str(item)] if str(item).strip() else []
        if group:
            groups.append(group)
    return groups


def _int_value(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default


def _contains(text: str, term: str) -> bool:
    return term.casefold() in text.casefold()


def _evidence_text(citations: list[dict[str, object]], sources: list[dict[str, object]]) -> str:
    parts: list[str] = []
    for item in citations + sources:
        for key in ("title", "text", "snippet", "url", "provider", "source_label"):
            value = item.get(key)
            if value is not None:
                parts.append(str(value))
    return "\n".join(parts)


def _add_check(
    checks: dict[str, dict[str, object]],
    failures: list[str],
    name: str,
    ok: bool,
    detail: str,
) -> None:
    checks[name] = {"ok": ok, "detail": detail}
    if not ok:
        failures.append(f"{name}: {detail}")


def _answer_strategy_name(data: dict[str, object]) -> str | None:
    strategy = data.get("answer_strategy")
    if isinstance(strategy, dict):
        name = strategy.get("name")
        if name is not None:
            return str(name)
    return None


def _backend_status(data: dict[str, object]) -> str | None:
    status = data.get("search_backend_status")
    if isinstance(status, dict) and status.get("status") is not None:
        return str(status["status"])
    return None


def evaluate_case_result(case: dict[str, object], data: dict[str, object], *, elapsed_ms: int) -> dict[str, object]:
    expected_domains = [domain.lower() for domain in _string_list(case.get("expected_domains"))]
    citations = _items(data.get("citations"))
    sources = _items(data.get("sources"))
    matched_citations = [
        citation for citation in citations if domain_matches(str(citation.get("url", "")), expected_domains)
    ]
    matched_sources = [source for source in sources if domain_matches(str(source.get("url", "")), expected_domains)]

    answer = str(data.get("answer", "") or "")
    evidence_text = _evidence_text(citations, sources)
    allow_direct_answer = bool(case.get("allow_direct_answer", False))
    min_answer_chars = _int_value(case.get("min_answer_chars"), 1)
    min_citations = _int_value(case.get("min_citations"), 0 if allow_direct_answer else 1)
    min_sources = _int_value(case.get("min_sources"), 0 if allow_direct_answer else 1)
    min_expected_citations = _int_value(
        case.get("min_expected_domain_citations"),
        1 if expected_domains and min_citations > 0 else 0,
    )
    min_expected_sources = _int_value(case.get("min_expected_domain_sources"), 0)

    checks: dict[str, dict[str, object]] = {}
    failures: list[str] = []
    _add_check(
        checks,
        failures,
        "answer_present",
        len(answer.strip()) >= min_answer_chars,
        f"answer chars={len(answer.strip())}, required>={min_answer_chars}",
    )
    _add_check(
        checks,
        failures,
        "citation_count",
        len(citations) >= min_citations,
        f"citations={len(citations)}, required>={min_citations}",
    )
    _add_check(
        checks,
        failures,
        "source_count",
        len(sources) >= min_sources,
        f"sources={len(sources)}, required>={min_sources}",
    )
    if expected_domains:
        _add_check(
            checks,
            failures,
            "expected_domain_citations",
            len(matched_citations) >= min_expected_citations,
            f"matched citations={len(matched_citations)}, required>={min_expected_citations}",
        )
        _add_check(
            checks,
            failures,
            "expected_domain_sources",
            len(matched_sources) >= min_expected_sources,
            f"matched sources={len(matched_sources)}, required>={min_expected_sources}",
        )

    for term in _string_list(case.get("required_answer_terms")):
        _add_check(
            checks,
            failures,
            f"answer_term:{term}",
            _contains(answer, term),
            f"answer must contain {term!r}",
        )
    for term in _string_list(case.get("required_evidence_terms")):
        _add_check(
            checks,
            failures,
            f"evidence_term:{term}",
            _contains(evidence_text, term),
            f"citations or sources must contain {term!r}",
        )
    for index, group in enumerate(_string_groups(case.get("required_any_answer_terms")), start=1):
        _add_check(
            checks,
            failures,
            f"answer_any_term:{index}",
            any(_contains(answer, term) for term in group),
            f"answer must contain one of {group!r}",
        )
    for index, group in enumerate(_string_groups(case.get("required_any_evidence_terms")), start=1):
        _add_check(
            checks,
            failures,
            f"evidence_any_term:{index}",
            any(_contains(evidence_text, term) for term in group),
            f"citations or sources must contain one of {group!r}",
        )

    forbidden_terms = _string_list(case.get("forbidden_answer_terms"))
    if not bool(case.get("allow_failure_answer", False)):
        forbidden_terms.extend(
            [
                "LM Studio synthesis failed",
                "I could not collect usable web evidence",
            ]
        )
    for term in forbidden_terms:
        _add_check(
            checks,
            failures,
            f"forbidden_answer_term:{term}",
            not _contains(answer, term),
            f"answer must not contain {term!r}",
        )

    expected_strategy = case.get("expected_answer_strategy")
    if expected_strategy:
        actual_strategy = _answer_strategy_name(data)
        _add_check(
            checks,
            failures,
            "answer_strategy",
            actual_strategy == str(expected_strategy),
            f"strategy={actual_strategy!r}, expected={expected_strategy!r}",
        )

    allowed_backend_statuses = _string_list(case.get("allowed_search_backend_statuses"))
    if allowed_backend_statuses:
        actual_status = _backend_status(data)
        _add_check(
            checks,
            failures,
            "search_backend_status",
            actual_status in allowed_backend_statuses,
            f"status={actual_status!r}, allowed={allowed_backend_statuses!r}",
        )

    if bool(case.get("require_validation_ok", False)):
        validation = data.get("validation")
        validation_ok = isinstance(validation, dict) and validation.get("ok") is True
        _add_check(checks, failures, "validation_ok", validation_ok, "validation.ok must be true")

    max_warnings = case.get("max_warnings")
    if isinstance(max_warnings, int):
        warnings = data.get("warnings", [])
        warning_count = len(warnings) if isinstance(warnings, list) else 0
        _add_check(
            checks,
            failures,
            "warning_count",
            warning_count <= max_warnings,
            f"warnings={warning_count}, allowed<={max_warnings}",
        )

    return {
        "ok": not failures,
        "failure_reasons": failures,
        "checks": checks,
        "elapsed_ms": elapsed_ms,
        "citation_count": len(citations),
        "source_count": len(sources),
        "expected_domain_citations": len(matched_citations),
        "expected_domain_sources": len(matched_sources),
        "expected_domain_required": bool(expected_domains),
    }


def filter_cases(
    cases: list[dict[str, object]],
    *,
    case_ids: list[str],
    categories: list[str],
    limit: int | None = None,
) -> list[dict[str, object]]:
    wanted_ids = set(case_ids)
    wanted_categories = set(categories)
    selected = [
        case
        for case in cases
        if (not wanted_ids or str(case.get("id")) in wanted_ids)
        and (not wanted_categories or str(case.get("category")) in wanted_categories)
    ]
    if limit is not None and limit >= 0:
        return selected[:limit]
    return selected


async def run_case(client: httpx.AsyncClient, api_url: str, case: dict[str, object], *, mode: str) -> dict[str, object]:
    started = time.perf_counter()
    payload = {
        "question": case["question"],
        "mode": mode,
        "freshness": case.get("freshness"),
    }
    try:
        response = await client.post(f"{api_url.rstrip('/')}/ask", json=payload)
        response.raise_for_status()
        data = response.json()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
    except Exception as exc:
        return {
            "id": case["id"],
            "category": case.get("category"),
            "ok": False,
            "error": str(exc),
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }

    warnings = data.get("warnings", [])
    answer = str(data.get("answer", ""))
    provider_health = data.get("provider_health", [])
    backend_status = data.get("search_backend_status", {})
    quality = evaluate_case_result(case, data, elapsed_ms=elapsed_ms)

    return {
        "id": case["id"],
        "category": case.get("category"),
        "ok": quality["ok"],
        "failure_reasons": quality["failure_reasons"],
        "checks": quality["checks"],
        "request_id": data.get("request_id"),
        "answer_strategy": data.get("answer_strategy", {}),
        "mode": data.get("mode"),
        "elapsed_ms": elapsed_ms,
        "pipeline_timings_ms": data.get("timings_ms", {}),
        "query_count": len(data.get("queries", [])),
        "source_count": quality["source_count"],
        "citation_count": quality["citation_count"],
        "expected_domain_citations": quality["expected_domain_citations"],
        "expected_domain_sources": quality["expected_domain_sources"],
        "expected_domain_required": quality["expected_domain_required"],
        "provider_failure_count": sum(1 for item in provider_health if isinstance(item, dict) and item.get("status") == "down"),
        "search_backend_status": backend_status.get("status") if isinstance(backend_status, dict) else None,
        "warnings": warnings,
        "answer_preview": answer[:300],
    }


def summarize(results: list[dict[str, object]]) -> dict[str, object]:
    ok_results = [result for result in results if result.get("ok")]
    latencies = sorted(int(result.get("elapsed_ms", 0)) for result in ok_results)

    def percentile(pct: float) -> int | None:
        if not latencies:
            return None
        index = min(len(latencies) - 1, round((len(latencies) - 1) * pct))
        return latencies[index]

    domain_results = [result for result in results if bool(result.get("expected_domain_required", True))]
    expected_hits = [result for result in domain_results if int(result.get("expected_domain_citations", 0)) > 0]
    citation_counts = [int(result.get("citation_count", 0)) for result in results]
    warning_counts = [len(result.get("warnings", []) or []) for result in results]
    provider_failures = [int(result.get("provider_failure_count", 0)) for result in results]
    failed_results = [result for result in results if not result.get("ok")]
    return {
        "cases": len(results),
        "ok": len(ok_results),
        "failed": len(failed_results),
        "all_passed": bool(results) and not failed_results,
        "failed_case_ids": [result.get("id") for result in failed_results],
        "success_rate": round(len(ok_results) / max(1, len(results)), 3),
        "expected_domain_cases": len(domain_results),
        "expected_domain_citation_rate": round(len(expected_hits) / max(1, len(domain_results)), 3),
        "p50_ms": percentile(0.5),
        "p90_ms": percentile(0.9),
        "avg_citation_count": round(sum(citation_counts) / max(1, len(results)), 2),
        "avg_warning_count": round(sum(warning_counts) / max(1, len(results)), 2),
        "provider_failure_count": sum(provider_failures),
    }


def _delta(current: object, baseline: object) -> int | float | None:
    if current is None or baseline is None:
        return None
    if isinstance(current, (int, float)) and isinstance(baseline, (int, float)):
        return round(current - baseline, 3)
    return None


def compare_reports(
    current: dict[str, object],
    baseline: dict[str, object],
    *,
    max_p90_regression_ms: int,
    min_success_rate: float | None,
    min_expected_domain_rate: float | None,
) -> dict[str, object]:
    current_summary = dict(current.get("summary", {}))
    baseline_summary = dict(baseline.get("summary", {}))
    metrics = {}
    for key in (
        "success_rate",
        "expected_domain_citation_rate",
        "p50_ms",
        "p90_ms",
        "avg_citation_count",
        "avg_warning_count",
        "provider_failure_count",
        "failed",
    ):
        metrics[key] = {
            "current": current_summary.get(key),
            "baseline": baseline_summary.get(key),
            "delta": _delta(current_summary.get(key), baseline_summary.get(key)),
        }

    failures: list[str] = []
    failed_count = current_summary.get("failed")
    if isinstance(failed_count, int) and failed_count > 0:
        failures.append(f"{failed_count} benchmark case(s) failed quality gates")
    p90_delta = metrics["p90_ms"]["delta"]
    if isinstance(p90_delta, (int, float)) and p90_delta > max_p90_regression_ms:
        failures.append(f"p90 latency regressed by {p90_delta}ms")
    success_rate = current_summary.get("success_rate")
    if min_success_rate is not None and isinstance(success_rate, (int, float)) and success_rate < min_success_rate:
        failures.append(f"success rate {success_rate} is below {min_success_rate}")
    expected_rate = current_summary.get("expected_domain_citation_rate")
    if (
        min_expected_domain_rate is not None
        and isinstance(expected_rate, (int, float))
        and expected_rate < min_expected_domain_rate
    ):
        failures.append(f"expected-domain citation rate {expected_rate} is below {min_expected_domain_rate}")

    return {
        "metrics": metrics,
        "failures": failures,
        "ok": not failures,
    }


async def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run local realtime search benchmark questions.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8787")
    parser.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    parser.add_argument("--out", default="")
    parser.add_argument("--baseline", default="")
    parser.add_argument("--compare-out", default="")
    parser.add_argument("--fail-on-regression", action="store_true")
    parser.add_argument("--max-p90-regression-ms", type=int, default=5000)
    parser.add_argument("--min-success-rate", type=float, default=None)
    parser.add_argument("--min-expected-domain-rate", type=float, default=None)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--mode", default="fast", help="Research mode to benchmark: fast, balanced, deep, or deepsearch.")
    parser.add_argument("--case-id", action="append", default=[], help="Run one case ID. Can be passed more than once.")
    parser.add_argument("--category", action="append", default=[], help="Run one category. Can be passed more than once.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the selected cases after filtering.")
    parser.add_argument("--list-cases", action="store_true", help="Print selected case IDs without running the API.")
    args = parser.parse_args()

    questions_path = Path(args.questions)
    all_cases = json.loads(questions_path.read_text(encoding="utf-8"))
    cases = filter_cases(all_cases, case_ids=args.case_id, categories=args.category, limit=args.limit)
    if args.list_cases:
        rendered_cases = [
            {"id": case.get("id"), "category": case.get("category"), "question": case.get("question")} for case in cases
        ]
        print(json.dumps(rendered_cases, ensure_ascii=False, indent=2))
        return 0
    if not cases:
        print("No benchmark cases matched the selected filters.", file=sys.stderr)
        return 2

    async with httpx.AsyncClient(timeout=args.timeout) as client:
        results = []
        for case in cases:
            print(f"running {case['id']}...", flush=True)
            result = await run_case(client, args.api_url, case, mode=args.mode)
            results.append(result)
            print(
                f"  ok={result.get('ok')} elapsed_ms={result.get('elapsed_ms')} "
                f"citations={result.get('citation_count', 0)} expected_citations={result.get('expected_domain_citations', 0)}",
                flush=True,
            )

    report = {"summary": summarize(results), "results": results}
    if args.baseline:
        baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        comparison = compare_reports(
            report,
            baseline,
            max_p90_regression_ms=args.max_p90_regression_ms,
            min_success_rate=args.min_success_rate,
            min_expected_domain_rate=args.min_expected_domain_rate,
        )
        report["comparison"] = comparison
        if args.compare_out:
            compare_out_path = Path(args.compare_out)
            compare_out_path.parent.mkdir(parents=True, exist_ok=True)
            compare_out_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    rendered = json.dumps(report, ensure_ascii=False, indent=2)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
    print(rendered)
    if args.fail_on_regression and report.get("comparison") and not dict(report["comparison"]).get("ok", False):
        return 1
    return 0 if report["summary"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
