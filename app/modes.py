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
    max_evidence_chunks: int
    max_evidence_chars: int
    search_timeout_seconds: float
    fetch_timeout_seconds: float
    synthesis_timeout_seconds: float
    lm_studio_max_tokens: int
    lm_studio_finalizer_max_tokens: int


def get_mode_profile(mode: str, settings: Settings) -> ModeProfile:
    requested = (mode or "fast").lower().strip()
    effective = requested if requested in {"fast", "balanced", "deep"} else "fast"

    if effective == "fast":
        return ModeProfile(
            requested_mode=requested,
            effective_mode="fast",
            answer_style="Answer concisely. Prefer the core answer and 3-5 citations.",
            max_query_variants=min(settings.max_query_variants, 4),
            max_candidate_urls=min(settings.max_candidate_urls, 16),
            max_fetch_urls=min(settings.max_fetch_urls, 8),
            max_evidence_chunks=min(settings.max_evidence_chunks, 8),
            max_evidence_chars=min(settings.max_evidence_chars, 10000),
            search_timeout_seconds=min(settings.search_timeout_seconds, 2.0),
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
            max_evidence_chunks=max(settings.max_evidence_chunks, 40),
            max_evidence_chars=max(settings.max_evidence_chars, 50000),
            search_timeout_seconds=max(settings.search_timeout_seconds, 4.0),
            fetch_timeout_seconds=max(settings.fetch_timeout_seconds, 5.0),
            synthesis_timeout_seconds=max(settings.synthesis_timeout_seconds, 420.0),
            lm_studio_max_tokens=max(settings.lm_studio_max_tokens, 8192),
            lm_studio_finalizer_max_tokens=max(settings.lm_studio_finalizer_max_tokens, 4096),
        )

    return ModeProfile(
        requested_mode=requested,
        effective_mode="balanced",
        answer_style="Answer with a balanced level of detail and cite the main claims.",
        max_query_variants=settings.max_query_variants,
        max_candidate_urls=settings.max_candidate_urls,
        max_fetch_urls=settings.max_fetch_urls,
        max_evidence_chunks=settings.max_evidence_chunks,
        max_evidence_chars=settings.max_evidence_chars,
        search_timeout_seconds=settings.search_timeout_seconds,
        fetch_timeout_seconds=settings.fetch_timeout_seconds,
        synthesis_timeout_seconds=settings.synthesis_timeout_seconds,
        lm_studio_max_tokens=settings.lm_studio_max_tokens,
        lm_studio_finalizer_max_tokens=settings.lm_studio_finalizer_max_tokens,
    )

