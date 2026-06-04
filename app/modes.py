from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings


@dataclass(frozen=True)
class ModeProfile:
    requested_mode: str
    effective_mode: str
    answer_style: str
    max_query_variants: int
    max_candidate_urls: int
    max_fetch_urls: int
    max_results_per_host: int
    max_evidence_chunks: int
    max_evidence_chars: int
    max_chunks_per_page: int
    search_result_limit: int
    mcp_max_citations: int
    mcp_max_sources: int
    mcp_citation_text_chars: int
    mcp_source_snippet_chars: int
    search_timeout_seconds: float
    fetch_timeout_seconds: float
    synthesis_timeout_seconds: float
    lm_studio_max_tokens: int
    lm_studio_finalizer_max_tokens: int


def get_mode_profile(mode: str, settings: Settings) -> ModeProfile:
    requested = (mode or "fast").lower().strip()
    aliases = {
        "deep-search": "deepsearch",
        "deep_search": "deepsearch",
        "research": "deepsearch",
    }
    effective = aliases.get(requested, requested)
    effective = effective if effective in {"fast", "balanced", "deep", "deepsearch"} else "fast"

    if effective == "fast":
        return ModeProfile(
            requested_mode=requested,
            effective_mode="fast",
            answer_style="Answer concisely. Prefer the core answer and 3-5 citations.",
            max_query_variants=min(settings.max_query_variants, 4),
            max_candidate_urls=min(settings.max_candidate_urls, 16),
            max_fetch_urls=min(settings.max_fetch_urls, 8),
            max_results_per_host=2,
            max_evidence_chunks=min(settings.max_evidence_chunks, 8),
            max_evidence_chars=min(settings.max_evidence_chars, 10000),
            max_chunks_per_page=2,
            search_result_limit=10,
            mcp_max_citations=12,
            mcp_max_sources=12,
            mcp_citation_text_chars=1200,
            mcp_source_snippet_chars=360,
            search_timeout_seconds=max(settings.search_timeout_seconds, 4.0),
            fetch_timeout_seconds=min(settings.fetch_timeout_seconds, 2.5),
            synthesis_timeout_seconds=min(settings.synthesis_timeout_seconds, 90.0),
            lm_studio_max_tokens=min(settings.lm_studio_max_tokens, 2400),
            lm_studio_finalizer_max_tokens=min(settings.lm_studio_finalizer_max_tokens, 1000),
        )

    if effective == "deep":
        return ModeProfile(
            requested_mode=requested,
            effective_mode="deep",
            answer_style="Answer thoroughly. Compare sources, surface uncertainty, and include detailed citations.",
            max_query_variants=max(settings.max_query_variants, 8),
            max_candidate_urls=max(settings.max_candidate_urls, 48),
            max_fetch_urls=max(settings.max_fetch_urls, 24),
            max_results_per_host=2,
            max_evidence_chunks=max(settings.max_evidence_chunks, 40),
            max_evidence_chars=max(settings.max_evidence_chars, 50000),
            max_chunks_per_page=2,
            search_result_limit=10,
            mcp_max_citations=20,
            mcp_max_sources=20,
            mcp_citation_text_chars=1600,
            mcp_source_snippet_chars=420,
            search_timeout_seconds=max(settings.search_timeout_seconds, 8.0),
            fetch_timeout_seconds=max(settings.fetch_timeout_seconds, 5.0),
            synthesis_timeout_seconds=max(settings.synthesis_timeout_seconds, 420.0),
            lm_studio_max_tokens=max(settings.lm_studio_max_tokens, 8192),
            lm_studio_finalizer_max_tokens=max(settings.lm_studio_finalizer_max_tokens, 4096),
        )

    if effective == "deepsearch":
        return ModeProfile(
            requested_mode=requested,
            effective_mode="deepsearch",
            answer_style=(
                "Answer like a deep research brief. Synthesize many sources, compare agreement and conflicts, "
                "separate confirmed facts from uncertainty, and cite the important claims densely."
            ),
            max_query_variants=max(settings.max_query_variants, 12),
            max_candidate_urls=max(settings.max_candidate_urls, 96),
            max_fetch_urls=max(settings.max_fetch_urls, 40),
            max_results_per_host=3,
            max_evidence_chunks=max(settings.max_evidence_chunks, 72),
            max_evidence_chars=max(settings.max_evidence_chars, 110000),
            max_chunks_per_page=3,
            search_result_limit=20,
            mcp_max_citations=36,
            mcp_max_sources=36,
            mcp_citation_text_chars=2200,
            mcp_source_snippet_chars=520,
            search_timeout_seconds=max(settings.search_timeout_seconds, 12.0),
            fetch_timeout_seconds=max(settings.fetch_timeout_seconds, 7.0),
            synthesis_timeout_seconds=max(settings.synthesis_timeout_seconds, 600.0),
            lm_studio_max_tokens=max(settings.lm_studio_max_tokens, 12000),
            lm_studio_finalizer_max_tokens=max(settings.lm_studio_finalizer_max_tokens, 6000),
        )

    return ModeProfile(
        requested_mode=requested,
        effective_mode="balanced",
        answer_style="Answer with a balanced level of detail and cite the main claims.",
        max_query_variants=settings.max_query_variants,
        max_candidate_urls=settings.max_candidate_urls,
        max_fetch_urls=settings.max_fetch_urls,
        max_results_per_host=2,
        max_evidence_chunks=settings.max_evidence_chunks,
        max_evidence_chars=settings.max_evidence_chars,
        max_chunks_per_page=2,
        search_result_limit=10,
        mcp_max_citations=16,
        mcp_max_sources=16,
        mcp_citation_text_chars=1400,
        mcp_source_snippet_chars=400,
        search_timeout_seconds=max(settings.search_timeout_seconds, 5.0),
        fetch_timeout_seconds=settings.fetch_timeout_seconds,
        synthesis_timeout_seconds=settings.synthesis_timeout_seconds,
        lm_studio_max_tokens=settings.lm_studio_max_tokens,
        lm_studio_finalizer_max_tokens=settings.lm_studio_finalizer_max_tokens,
    )
