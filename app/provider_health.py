from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchTrace:
    provider: str
    query: str
    freshness: str | None
    cache_hit: bool
    result_count: int
    elapsed_ms: int
    error: str | None = None


def summarize_search_traces(traces: list[SearchTrace]) -> list[dict[str, object]]:
    by_provider: dict[str, dict[str, object]] = {}

    for trace in traces:
        summary = by_provider.setdefault(
            trace.provider,
            {
                "provider": trace.provider,
                "requests": 0,
                "successes": 0,
                "failures": 0,
                "cache_hits": 0,
                "result_count": 0,
                "elapsed_total_ms": 0,
            },
        )
        summary["requests"] = int(summary["requests"]) + 1
        summary["result_count"] = int(summary["result_count"]) + trace.result_count
        summary["elapsed_total_ms"] = int(summary["elapsed_total_ms"]) + trace.elapsed_ms
        if trace.cache_hit:
            summary["cache_hits"] = int(summary["cache_hits"]) + 1
        if trace.error:
            summary["failures"] = int(summary["failures"]) + 1
        else:
            summary["successes"] = int(summary["successes"]) + 1

    rendered = []
    for summary in by_provider.values():
        requests = int(summary["requests"])
        failures = int(summary["failures"])
        result_count = int(summary["result_count"])
        avg_elapsed_ms = round(int(summary.pop("elapsed_total_ms")) / max(1, requests))
        if failures == requests:
            status = "down"
        elif failures:
            status = "degraded"
        elif result_count == 0:
            status = "empty"
        else:
            status = "ok"
        rendered.append(summary | {"avg_elapsed_ms": avg_elapsed_ms, "status": status})

    return sorted(rendered, key=lambda item: str(item["provider"]))
