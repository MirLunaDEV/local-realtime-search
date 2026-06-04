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

    expected_domains = list(case.get("expected_domains", []))
    citations = data.get("citations", [])
    sources = data.get("sources", [])
    matched_citations = [
        citation for citation in citations if domain_matches(str(citation.get("url", "")), expected_domains)
    ]
    matched_sources = [source for source in sources if domain_matches(str(source.get("url", "")), expected_domains)]
    warnings = data.get("warnings", [])
    answer = str(data.get("answer", ""))
    provider_health = data.get("provider_health", [])
    backend_status = data.get("search_backend_status", {})

    return {
        "id": case["id"],
        "category": case.get("category"),
        "ok": bool(answer and citations),
        "request_id": data.get("request_id"),
        "answer_strategy": data.get("answer_strategy", {}),
        "mode": data.get("mode"),
        "elapsed_ms": elapsed_ms,
        "pipeline_timings_ms": data.get("timings_ms", {}),
        "query_count": len(data.get("queries", [])),
        "source_count": len(sources),
        "citation_count": len(citations),
        "expected_domain_citations": len(matched_citations),
        "expected_domain_sources": len(matched_sources),
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

    expected_hits = [result for result in results if int(result.get("expected_domain_citations", 0)) > 0]
    citation_counts = [int(result.get("citation_count", 0)) for result in results]
    warning_counts = [len(result.get("warnings", []) or []) for result in results]
    provider_failures = [int(result.get("provider_failure_count", 0)) for result in results]
    return {
        "cases": len(results),
        "ok": len(ok_results),
        "success_rate": round(len(ok_results) / max(1, len(results)), 3),
        "expected_domain_citation_rate": round(len(expected_hits) / max(1, len(results)), 3),
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
    ):
        metrics[key] = {
            "current": current_summary.get(key),
            "baseline": baseline_summary.get(key),
            "delta": _delta(current_summary.get(key), baseline_summary.get(key)),
        }

    failures: list[str] = []
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
    args = parser.parse_args()

    questions_path = Path(args.questions)
    cases = json.loads(questions_path.read_text(encoding="utf-8"))

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
    return 0 if report["summary"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
