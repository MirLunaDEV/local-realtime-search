from __future__ import annotations

from dataclasses import dataclass

from app.answer_strategy import classify_answer_strategy
from app.config import Settings


_EXPLICIT_MODES = {"fast", "balanced", "deep", "deepsearch"}
_AUTO_MODES = {"", "auto", "adaptive", "smart"}


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


@dataclass(frozen=True)
class AdaptiveModeSelection:
    requested_mode: str
    selected_mode: str
    auto: bool
    reason: str
    answer_strategy: str
    freshness: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_mode": self.requested_mode,
            "selected_mode": self.selected_mode,
            "auto": self.auto,
            "reason": self.reason,
            "answer_strategy": self.answer_strategy,
            "freshness": self.freshness,
        }


def _normalized_mode(mode: str) -> str:
    requested = (mode or "auto").lower().strip()
    aliases = {
        "deep-search": "deepsearch",
        "deep_search": "deepsearch",
        "research": "deepsearch",
    }
    return aliases.get(requested, requested)


def select_research_mode(
    question: str,
    *,
    requested_mode: str,
    requested_freshness: str | None,
    direct_answer_label: str | None = None,
) -> AdaptiveModeSelection:
    requested = (requested_mode or "auto").lower().strip()
    normalized = _normalized_mode(requested)
    strategy = classify_answer_strategy(
        question,
        requested_freshness=requested_freshness,
        direct_answer_label=direct_answer_label,
    )

    if normalized not in _AUTO_MODES:
        selected = normalized if normalized in _EXPLICIT_MODES else "fast"
        reason = "explicit_mode" if normalized in _EXPLICIT_MODES else "unknown_mode_fallback"
        return AdaptiveModeSelection(
            requested_mode=requested,
            selected_mode=selected,
            auto=False,
            reason=reason,
            answer_strategy=strategy.name,
            freshness=strategy.freshness,
        )

    if direct_answer_label is not None:
        selected = "fast"
        reason = "direct_runtime_answer"
    elif strategy.name == "weather":
        selected = "fast"
        reason = "weather_provider_shortcut"
    elif strategy.name == "benchmark":
        selected = "deepsearch"
        reason = "benchmark_requires_broad_evidence"
    elif strategy.name == "comparison":
        selected = "deep"
        reason = "comparison_needs_multiple_sources"
    elif strategy.name == "docs_lookup":
        selected = "balanced"
        reason = "official_docs_need_moderate_context"
    elif strategy.name == "current_fact":
        selected = "balanced"
        reason = "current_fact_needs_verification"
    else:
        selected = "balanced"
        reason = "general_research_default"

    return AdaptiveModeSelection(
        requested_mode=requested,
        selected_mode=selected,
        auto=True,
        reason=reason,
        answer_strategy=strategy.name,
        freshness=strategy.freshness,
    )


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
