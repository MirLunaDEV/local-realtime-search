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


def _evidence_status(
    context: Mapping[str, Any],
    *,
    direct_answer: object,
    citations: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    no_evidence: bool,
) -> dict[str, Any]:
    backend_status = context.get("search_backend_status")
    backend_state = backend_status.get("status") if isinstance(backend_status, Mapping) else None
    total_citations = len([item for item in (context.get("citations", []) or []) if isinstance(item, Mapping)])
    total_sources = len([item for item in (context.get("sources", []) or []) if isinstance(item, Mapping)])

    if no_evidence:
        status = "empty"
        guidance = (
            "No cited evidence was collected. Report that clearly, do not invent facts, and do not call "
            "local_research again for the same question in this turn."
        )
    elif direct_answer is not None:
        status = "direct_answer"
        guidance = "The tool answered directly from local/runtime data. Write the final answer now."
    elif citations:
        status = "ok" if len(citations) >= 3 else "partial"
        guidance = (
            "Evidence collection succeeded because cited evidence is present. If SearXNG or DuckDuckGo are empty, "
            "mention that only as provider coverage context, not as a failed research result."
        )
    else:
        status = "empty"
        guidance = "No cited evidence or direct answer was available. Report that clearly without inventing facts."

    return {
        "status": status,
        "ready_to_answer": direct_answer is not None or bool(citations) or no_evidence,
        "payload_citation_count": len(citations),
        "payload_source_count": len(sources),
        "total_citation_count": total_citations,
        "total_source_count": total_sources,
        "search_backend_status": backend_state,
        "search_backend_required_for_success": False,
        "guidance": guidance,
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
    no_evidence = direct_answer is None and not citations
    if no_evidence:
        direct_answer = (
            "I could not collect usable cited web evidence for this request. Do not call local_research again for the "
            "same question in this turn. Do not provide estimated benchmark scores, guessed community reviews, fake "
            "tables, or uncited claims. Tell the user that local evidence collection failed, mention the warnings/"
            "provider status, and suggest retrying after SearXNG is healthy or using a narrower query."
        )
    evidence_status = _evidence_status(
        context,
        direct_answer=direct_answer,
        citations=citations,
        sources=sources,
        no_evidence=no_evidence,
    )

    return {
        "tool": "local_research",
        "next_action": "write_final_answer",
        "ready_to_answer": evidence_status["ready_to_answer"],
        "answer_direct": direct_answer,
        "synthesis_contract": {
            "tool_use_complete": True,
            "write_final_answer_now": True,
            "do_not_call_tools_again_for_same_question": True,
            "do_not_output_reasoning_trace": True,
            "answer_language": "match_user",
            "citation_style": "Use bracket citation IDs like [1] for claims from evidence.",
            "empty_backend_policy": (
                "Do not describe the whole research as failed only because SearXNG/DuckDuckGo are empty when citations exist."
            ),
        },
        "instruction_to_model": (
            "Tool use is complete. Write the final answer now in the user's language and normal assistant content; "
            "do not output a reasoning trace and do not call local_research again for the same question. If "
            "answer_direct is present, answer directly from it. Otherwise answer using only the evidence citations "
            "below, cite claims with bracket IDs like [1], and mention uncertainty when warnings or provider health "
            "indicate weak coverage. If citations exist, do not say the whole research failed only because SearXNG "
            "or DuckDuckGo are empty/degraded. In deepsearch mode, write a structured research brief with source "
            "agreement, disagreements, and remaining unknowns. Follow answer_strategy.guidance when present. If "
            "citations are empty, report the failed evidence collection instead of inventing facts."
        ),
        "terminal_result": True,
        "citations_empty": not citations,
        "tool_call_policy": {
            "call_again_for_same_question": False,
            "reason": "This MCP result is terminal for the current user question, even when citations are empty.",
        },
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
        "evidence_status": evidence_status,
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
