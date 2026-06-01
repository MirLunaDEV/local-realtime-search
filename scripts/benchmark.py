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


async def run_case(client: httpx.AsyncClient, api_url: str, case: dict[str, object]) -> dict[str, object]:
    started = time.perf_counter()
    payload = {
        "question": case["question"],
        "mode": "fast",
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

    return {
        "id": case["id"],
        "category": case.get("category"),
        "ok": bool(answer and citations),
        "elapsed_ms": elapsed_ms,
        "pipeline_timings_ms": data.get("timings_ms", {}),
        "query_count": len(data.get("queries", [])),
        "source_count": len(sources),
        "citation_count": len(citations),
        "expected_domain_citations": len(matched_citations),
        "expected_domain_sources": len(matched_sources),
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
    return {
        "cases": len(results),
        "ok": len(ok_results),
        "success_rate": round(len(ok_results) / max(1, len(results)), 3),
        "expected_domain_citation_rate": round(len(expected_hits) / max(1, len(results)), 3),
        "p50_ms": percentile(0.5),
        "p90_ms": percentile(0.9),
    }


async def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run local realtime search benchmark questions.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8787")
    parser.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    parser.add_argument("--out", default="")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    questions_path = Path(args.questions)
    cases = json.loads(questions_path.read_text(encoding="utf-8"))

    async with httpx.AsyncClient(timeout=args.timeout) as client:
        results = []
        for case in cases:
            print(f"running {case['id']}...", flush=True)
            result = await run_case(client, args.api_url, case)
            results.append(result)
            print(
                f"  ok={result.get('ok')} elapsed_ms={result.get('elapsed_ms')} "
                f"citations={result.get('citation_count', 0)} expected_citations={result.get('expected_domain_citations', 0)}",
                flush=True,
            )

    report = {"summary": summarize(results), "results": results}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0 if report["summary"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
