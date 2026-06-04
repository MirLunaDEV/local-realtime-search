from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit


def _trim(value: object, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return f"{text[: limit - 3].rstrip()}..."


def _profile_int(profile: object, key: str, default: int) -> int:
    if isinstance(profile, Mapping):
        value = profile.get(key)
        if isinstance(value, int) and value > 0:
            return value
    return default


def _compact_citation(citation: Mapping[str, Any], *, text_chars: int) -> dict[str, Any]:
    return {
        "id": citation.get("id"),
        "title": _trim(citation.get("title"), 180),
        "url": citation.get("url"),
        "text": _trim(citation.get("text"), text_chars),
        "provider": citation.get("provider"),
        "published_or_updated": citation.get("published_or_updated"),
        "source_type": citation.get("source_type"),
    }


def _compact_source(source: Mapping[str, Any], *, snippet_chars: int) -> dict[str, Any]:
    return {
        "title": _trim(source.get("title"), 180),
        "url": source.get("url"),
        "snippet": _trim(source.get("snippet"), snippet_chars),
        "provider": source.get("provider"),
        "published_or_updated": source.get("published_or_updated"),
        "source_label": source.get("source_label"),
        "score": source.get("score"),
    }


def _source_summary(sources: list[dict[str, Any]]) -> dict[str, Any]:
    labels: dict[str, int] = {}
    hosts: dict[str, int] = {}
    for source in sources:
        label = str(source.get("source_label") or "unknown")
        labels[label] = labels.get(label, 0) + 1
        url = str(source.get("url") or "")
        host = urlsplit(url).netloc
        if host:
            hosts[host] = hosts.get(host, 0) + 1
    return {
        "source_label_counts": labels,
        "top_hosts": dict(sorted(hosts.items(), key=lambda item: item[1], reverse=True)[:8]),
    }


def format_mcp_research_payload(
    context: Mapping[str, Any],
    *,
    max_citations: int | None = None,
    max_sources: int | None = None,
) -> dict[str, Any]:
    """Compress pipeline output into a model-friendly MCP tool result."""
    direct_answer = context.get("direct_answer")
    answer_strategy = context.get("answer_strategy") if isinstance(context.get("answer_strategy"), Mapping) else {}
    mode_profile = context.get("mode_profile")
    citation_count = max_citations or _profile_int(mode_profile, "mcp_max_citations", 12)
    source_count = max_sources or _profile_int(mode_profile, "mcp_max_sources", 12)
    citation_text_chars = _profile_int(mode_profile, "mcp_citation_text_chars", 1200)
    source_snippet_chars = _profile_int(mode_profile, "mcp_source_snippet_chars", 360)
    citations = [
        _compact_citation(citation, text_chars=citation_text_chars)
        for citation in list(context.get("citations", []))[:citation_count]
        if isinstance(citation, Mapping)
    ]
    sources = [
        _compact_source(source, snippet_chars=source_snippet_chars)
        for source in list(context.get("sources", []))[:source_count]
        if isinstance(source, Mapping)
    ]

    return {
        "tool": "local_research",
        "answer_direct": direct_answer,
        "instruction_to_model": (
            "If answer_direct is present, answer directly from it. Otherwise answer using only the "
            "evidence citations below, cite claims with bracket IDs like [1], and mention uncertainty "
            "when warnings or provider health indicate weak coverage. In deepsearch mode, write a structured "
            "research brief with source agreement, disagreements, and remaining unknowns. Follow "
            "answer_strategy.guidance when present."
        ),
        "answer_strategy": answer_strategy,
        "request_id": context.get("request_id"),
        "mode": context.get("mode"),
        "requested_mode": context.get("requested_mode"),
        "freshness": context.get("freshness"),
        "requested_freshness": context.get("requested_freshness"),
        "queries": context.get("queries", []),
        "citations": citations,
        "sources": sources,
        "payload_budget": {
            "max_citations": citation_count,
            "max_sources": source_count,
            "citation_text_chars": citation_text_chars,
            "source_snippet_chars": source_snippet_chars,
        },
        "source_summary": _source_summary(sources),
        "provider_health": context.get("provider_health", []),
        "search_backend_status": context.get("search_backend_status", {}),
        "weather_provider_status": context.get("weather_provider_status", {}),
        "warnings": context.get("warnings", []),
        "confidence": context.get("confidence"),
        "timings_ms": context.get("timings_ms", {}),
        "cache_hits": context.get("cache_hits", {}),
        "fetcher_counts": context.get("fetcher_counts", {}),
        "knowledge_prior": context.get("knowledge_prior"),
        "config": context.get("config", {}),
    }
