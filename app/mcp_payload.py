from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _compact_citation(citation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": citation.get("id"),
        "title": citation.get("title"),
        "url": citation.get("url"),
        "text": citation.get("text"),
        "provider": citation.get("provider"),
        "published_or_updated": citation.get("published_or_updated"),
        "source_type": citation.get("source_type"),
    }


def _compact_source(source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "title": source.get("title"),
        "url": source.get("url"),
        "snippet": source.get("snippet"),
        "provider": source.get("provider"),
        "published_or_updated": source.get("published_or_updated"),
        "source_label": source.get("source_label"),
        "score": source.get("score"),
    }


def format_mcp_research_payload(
    context: Mapping[str, Any],
    *,
    max_citations: int = 12,
    max_sources: int = 12,
) -> dict[str, Any]:
    """Compress pipeline output into a model-friendly MCP tool result."""
    direct_answer = context.get("direct_answer")
    citations = [
        _compact_citation(citation)
        for citation in list(context.get("citations", []))[:max_citations]
        if isinstance(citation, Mapping)
    ]
    sources = [
        _compact_source(source)
        for source in list(context.get("sources", []))[:max_sources]
        if isinstance(source, Mapping)
    ]

    return {
        "tool": "local_research",
        "answer_direct": direct_answer,
        "instruction_to_model": (
            "If answer_direct is present, answer directly from it. Otherwise answer using only the "
            "evidence citations below, cite claims with bracket IDs like [1], and mention uncertainty "
            "when warnings or provider health indicate weak coverage."
        ),
        "mode": context.get("mode"),
        "requested_mode": context.get("requested_mode"),
        "queries": context.get("queries", []),
        "citations": citations,
        "sources": sources,
        "provider_health": context.get("provider_health", []),
        "warnings": context.get("warnings", []),
        "confidence": context.get("confidence"),
        "timings_ms": context.get("timings_ms", {}),
        "cache_hits": context.get("cache_hits", {}),
        "fetcher_counts": context.get("fetcher_counts", {}),
        "knowledge_prior": context.get("knowledge_prior"),
    }
