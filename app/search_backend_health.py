from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from urllib.parse import urljoin

import httpx

from app.config import Settings


@dataclass(frozen=True)
class SearchBackendStatus:
    provider: str
    status: str
    base_url: str
    elapsed_ms: int
    result_count: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def status_from_provider_health(provider_health: list[dict[str, object]], settings: Settings) -> SearchBackendStatus:
    for item in provider_health:
        if item.get("provider") != "searxng":
            continue
        status = str(item.get("status") or "unknown")
        requests = int(item.get("requests") or 0)
        result_count = int(item.get("result_count") or 0)
        elapsed_ms = int(item.get("avg_elapsed_ms") or 0)
        if status == "down":
            error = "SearXNG did not respond during the research run."
        elif status == "degraded":
            error = "SearXNG responded inconsistently; some search requests failed or timed out during the research run."
        elif status == "empty":
            error = "SearXNG responded but returned no search results."
        else:
            error = None
        return SearchBackendStatus(
            provider="searxng",
            status=status,
            base_url=settings.searxng_base_url,
            elapsed_ms=elapsed_ms,
            result_count=result_count,
            error=error if requests else "SearXNG was not queried.",
        )
    return SearchBackendStatus(
        provider="searxng",
        status="not_used",
        base_url=settings.searxng_base_url,
        elapsed_ms=0,
        error="SearXNG was not needed for this request.",
    )


async def check_search_backend(settings: Settings, *, query: str = "python") -> SearchBackendStatus:
    started = time.perf_counter()
    params = {
        "q": query,
        "format": "json",
        "language": "auto",
        "safesearch": 0,
    }
    try:
        async with httpx.AsyncClient(timeout=max(settings.search_timeout_seconds, 8.0), follow_redirects=True) as client:
            response = await client.get(urljoin(settings.searxng_base_url.rstrip("/") + "/", "search"), params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        return SearchBackendStatus(
            provider="searxng",
            status="down",
            base_url=settings.searxng_base_url,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            error=(str(exc) or exc.__class__.__name__)[:300],
        )

    result_count = len(payload.get("results", [])) if isinstance(payload, dict) else 0
    unresponsive = payload.get("unresponsive_engines", []) if isinstance(payload, dict) else []
    unresponsive_count = len(unresponsive) if isinstance(unresponsive, list) else 0
    status = "ok" if result_count else "empty"
    error = None if result_count else "SearXNG returned JSON but no results."
    if result_count and unresponsive_count:
        status = "degraded"
        names = []
        for item in unresponsive[:5] if isinstance(unresponsive, list) else []:
            if isinstance(item, list) and item:
                names.append(str(item[0]))
        detail = ", ".join(names) if names else f"{unresponsive_count} engine(s)"
        error = f"SearXNG returned results, but {detail} were unresponsive."
    return SearchBackendStatus(
        provider="searxng",
        status=status,
        base_url=settings.searxng_base_url,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        result_count=result_count,
        error=error,
    )
