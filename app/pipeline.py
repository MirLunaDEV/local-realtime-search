from __future__ import annotations

import asyncio
import time
from dataclasses import asdict

from app.answer_cleanup import cleanup_answer_for_prior
from app.answer_strategy import classify_answer_strategy
from app.cache import SearchCache
from app.config import Settings
from app.config_validation import config_warnings, validate_settings
from app.direct_answers import maybe_direct_answer
from app.evidence import EvidenceChunk, evidence_from_page, evidence_from_snippet, select_evidence
from app.fetch.fetcher import fetch_page_best_effort
from app.fetch.http_fetcher import FetchedPage
from app.freshness import infer_freshness
from app.knowledge_prior import get_knowledge_prior
from app.lmstudio import EmptyFinalContentError, LmStudioClient
from app.modes import get_mode_profile
from app.planner import plan_queries
from app.prompts import build_answer_messages, build_finalizer_messages
from app.provider_health import SearchTrace, summarize_search_traces
from app.ranking import rank_results, select_diverse_results
from app.request_id import new_request_id
from app.search.base import SearchResult
from app.search.duckduckgo import DuckDuckGoHtmlProvider
from app.search.official_hints import OfficialHintsProvider
from app.search.searxng import SearxngProvider
from app.search_backend_health import status_from_provider_health
from app.security import UnsafeUrlError, ensure_url_safe_for_fetch
from app.source_policy import source_warning
from app.validator import validate_answer
from app.weather import WeatherEvidence, WeatherProviderStatus, collect_weather_evidence


FRESHNESS_MAP = {
    "day": "day",
    "week": "week",
    "month": "month",
    "year": "year",
}


def _search_cache_key(provider: object, query: str, freshness: str | None) -> str:
    provider_name = str(getattr(provider, "name", provider.__class__.__name__))
    return f"{provider_name}|{freshness or ''}|{query}"


async def _safe_search(
    provider: object,
    query: str,
    freshness: str | None,
    cache: SearchCache,
    ttl_seconds: int,
) -> tuple[list[SearchResult], SearchTrace]:
    started = time.perf_counter()
    provider_name = str(getattr(provider, "name", provider.__class__.__name__))
    key = _search_cache_key(provider, query, freshness)
    cached = cache.get_search(key, ttl_seconds)
    if cached:
        return cached, SearchTrace(
            provider=provider_name,
            query=query,
            freshness=freshness,
            cache_hit=True,
            result_count=len(cached),
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
    try:
        results = await provider.search(query, freshness=FRESHNESS_MAP.get(freshness or ""), limit=10)
        if results:
            cache.set_search(key, results)
        return results, SearchTrace(
            provider=provider_name,
            query=query,
            freshness=freshness,
            cache_hit=False,
            result_count=len(results),
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:
        detail = str(exc) or exc.__class__.__name__
        return [], SearchTrace(
            provider=provider_name,
            query=query,
            freshness=freshness,
            cache_hit=False,
            result_count=0,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            error=detail[:300],
        )


async def _safe_fetch(
    result: SearchResult,
    timeout_seconds: float,
    cache: SearchCache,
    ttl_seconds: int,
    fetcher: str,
    crawl4ai_timeout_seconds: float,
    allow_private_network_fetch: bool,
    resolve_fetch_hostnames: bool,
) -> tuple[SearchResult, FetchedPage | None, bool, str]:
    try:
        ensure_url_safe_for_fetch(
            result.url,
            allow_private_network=allow_private_network_fetch,
            resolve_hostnames=resolve_fetch_hostnames,
        )
    except UnsafeUrlError:
        return result, None, False, "blocked_url"

    cached = cache.get_page(result.url, ttl_seconds)
    if cached is not None:
        return result, cached, True, "cache"
    try:
        page, used_fetcher = await fetch_page_best_effort(
            result.url,
            fetcher=fetcher,
            http_timeout_seconds=timeout_seconds,
            crawl4ai_timeout_seconds=crawl4ai_timeout_seconds,
            allow_private_network=allow_private_network_fetch,
            resolve_hostnames=resolve_fetch_hostnames,
            skip_url_safety_check=True,
        )
        cache.set_page(result.url, page)
        return result, page, False, used_fetcher
    except UnsafeUrlError:
        return result, None, False, "blocked_url"
    except Exception:
        return result, None, False, "failed"


def _warnings(
    evidence: list[EvidenceChunk],
    searched_count: int,
    fetched_count: int,
    search_backend_status: dict[str, object] | None = None,
    weather_provider_status: dict[str, object] | None = None,
    fetcher_counts: dict[str, int] | None = None,
) -> list[str]:
    warnings: list[str] = []
    blocked_count = (fetcher_counts or {}).get("blocked_url", 0)
    if blocked_count:
        warnings.append(f"Blocked {blocked_count} unsafe URL(s) before fetching.")
    if weather_provider_status and weather_provider_status.get("status") in {"down", "skipped"}:
        detail = weather_provider_status.get("error")
        warnings.append(f"Weather provider is {weather_provider_status.get('status')}: {detail}")
    if search_backend_status and search_backend_status.get("status") in {"down", "empty"}:
        status = search_backend_status.get("status")
        base_url = search_backend_status.get("base_url")
        warnings.append(f"SearXNG search backend is {status} at {base_url}; using fallback sources only.")
    if not evidence:
        warnings.append("No usable web evidence was collected.")
    elif all(chunk.source_type == "snippet" for chunk in evidence):
        warnings.append("Only search snippets were available; full pages could not be fetched.")
    if fetched_count < min(3, searched_count):
        warnings.append("Few pages were fetched successfully, so coverage may be thin.")
    source_warnings = {
        warning
        for chunk in evidence
        if (warning := source_warning(chunk.url, chunk.title)) is not None
    }
    warnings.extend(sorted(source_warnings)[:5])
    return warnings


async def collect_research_context(question: str, *, mode: str, freshness: str | None, settings: Settings) -> dict[str, object]:
    request_id = new_request_id()
    started = time.perf_counter()
    marks: dict[str, int] = {}
    cache = SearchCache(settings.cache_path)
    cache_hits = {"search": 0, "page": 0}
    fetcher_counts: dict[str, int] = {}
    profile = get_mode_profile(mode, settings)
    effective_freshness = infer_freshness(question, freshness)
    config_status = validate_settings(settings)
    settings_warnings = config_warnings(config_status)

    direct_answer = maybe_direct_answer(question, settings.local_timezone)
    if direct_answer is not None:
        answer_strategy = classify_answer_strategy(
            question,
            requested_freshness=freshness,
            direct_answer_label=direct_answer.label,
        ).to_dict()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "direct_answer": direct_answer.answer,
            "queries": [],
            "citations": [],
            "sources": [],
            "timings_ms": {
                "planning": elapsed_ms,
                "search": 0,
                "fetch": 0,
                "synthesis": 0,
                "total": elapsed_ms,
            },
            "cache_hits": cache_hits,
            "fetcher_counts": fetcher_counts,
            "search_traces": [],
            "provider_health": [],
            "search_backend_status": {
                "provider": "searxng",
                "status": "not_used",
                "base_url": settings.searxng_base_url,
                "elapsed_ms": 0,
                "result_count": 0,
                "error": "Direct answer did not need web search.",
            },
            "weather_provider_status": {
                "provider": "wttr_in",
                "status": "not_used",
                "location": None,
                "elapsed_ms": 0,
                "error": "Direct answer did not need weather.",
            },
            "confidence": "high",
            "warnings": settings_warnings,
            "request_id": request_id,
            "config": config_status,
            "validation": {
                "ok": True,
                "issues": [],
                "cited_ids": [],
                "missing_citation_ids": [],
            },
            "mode": profile.effective_mode,
            "requested_mode": profile.requested_mode,
            "freshness": effective_freshness,
            "requested_freshness": freshness,
            "answer_strategy": answer_strategy,
            "mode_profile": asdict(profile),
            "model": settings.lm_studio_model,
            "knowledge_prior": {"label": direct_answer.label, "text": "Answered directly from the local runtime clock."},
            "_evidence_chunks": [],
        }

    queries = plan_queries(question, max_queries=profile.max_query_variants, freshness=effective_freshness)
    prior = get_knowledge_prior(question)
    answer_strategy = classify_answer_strategy(question, requested_freshness=freshness).to_dict()
    marks["planning"] = int((time.perf_counter() - started) * 1000)

    weather_result = await collect_weather_evidence(question, timeout_seconds=settings.weather_timeout_seconds)
    if isinstance(weather_result, WeatherEvidence):
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        weather_provider_status = weather_result.status.to_dict()
        search_backend_status = {
            "provider": "searxng",
            "status": "not_used",
            "base_url": settings.searxng_base_url,
            "elapsed_ms": 0,
            "result_count": 0,
            "error": "Weather provider answered this request before web search.",
        }
        source = asdict(weather_result.source) | {
            "canonical_url": weather_result.source.url,
            "score": 50.0,
            "source_label": "weather_provider",
        }
        return {
            "direct_answer": None,
            "queries": queries,
            "citations": [asdict(weather_result.evidence)],
            "sources": [source],
            "timings_ms": {
                "planning": marks["planning"],
                "search": weather_result.status.elapsed_ms,
                "fetch": 0,
                "synthesis": 0,
                "total": elapsed_ms,
            },
            "cache_hits": cache_hits,
            "fetcher_counts": fetcher_counts,
            "search_traces": [],
            "provider_health": [],
            "search_backend_status": search_backend_status,
            "weather_provider_status": weather_provider_status,
            "confidence": "high",
            "warnings": settings_warnings,
            "request_id": request_id,
            "config": config_status,
            "mode": profile.effective_mode,
            "requested_mode": profile.requested_mode,
            "freshness": effective_freshness,
            "requested_freshness": freshness,
            "answer_strategy": answer_strategy,
            "mode_profile": asdict(profile),
            "model": settings.lm_studio_model,
            "knowledge_prior": asdict(prior) if prior else None,
            "_evidence_chunks": [weather_result.evidence],
        }
    weather_provider_status = (
        weather_result.to_dict() if isinstance(weather_result, WeatherProviderStatus) else {"status": "unknown"}
    )

    search_providers = [
        OfficialHintsProvider(),
        SearxngProvider(settings.searxng_base_url, timeout_seconds=profile.search_timeout_seconds),
        DuckDuckGoHtmlProvider(timeout_seconds=profile.search_timeout_seconds),
    ]
    search_tasks = [
        _safe_search(provider, query, effective_freshness, cache, settings.search_cache_ttl_seconds)
        for provider in search_providers
        for query in queries
    ]
    search_batches = await asyncio.gather(*search_tasks)
    search_results = []
    search_traces = []
    for batch, trace in search_batches:
        search_traces.append(trace)
        if trace.cache_hit:
            cache_hits["search"] += 1
        search_results.extend(batch)
    marks["search"] = int((time.perf_counter() - started) * 1000)

    ranked = rank_results(search_results, question, limit=profile.max_candidate_urls)
    selected_for_fetch = select_diverse_results(ranked, profile.max_fetch_urls)
    fetch_targets = [item.result for item in selected_for_fetch]

    fetch_pairs = await asyncio.gather(
        *[
            _safe_fetch(
                result,
                profile.fetch_timeout_seconds,
                cache,
                settings.page_cache_ttl_seconds,
                settings.fetcher,
                settings.crawl4ai_timeout_seconds,
                settings.allow_private_network_fetch,
                settings.resolve_fetch_hostnames,
            )
            for result in fetch_targets
        ]
    )
    evidence: list[EvidenceChunk] = []
    next_id = 1
    fetched_count = 0
    for source, page, cache_hit, used_fetcher in fetch_pairs:
        fetcher_counts[used_fetcher] = fetcher_counts.get(used_fetcher, 0) + 1
        if cache_hit:
            cache_hits["page"] += 1
        if page is None:
            if used_fetcher == "blocked_url":
                continue
            snippet = evidence_from_snippet(source, next_id)
            if snippet:
                evidence.append(snippet)
                next_id += 1
            continue
        fetched_count += 1
        chunks = evidence_from_page(source, page, next_id, max_chunks=2)
        evidence.extend(chunks)
        next_id += len(chunks)
        if len(evidence) >= profile.max_evidence_chunks:
            break
    evidence = select_evidence(evidence, question, profile.max_evidence_chunks, profile.max_evidence_chars)
    marks["fetch"] = int((time.perf_counter() - started) * 1000)

    timings = {
        "planning": marks["planning"],
        "search": marks["search"] - marks["planning"],
        "fetch": marks["fetch"] - marks["search"],
        "synthesis": 0,
        "total": marks["fetch"],
    }

    provider_health = summarize_search_traces(search_traces)
    search_backend_status = status_from_provider_health(provider_health, settings).to_dict()

    return {
        "direct_answer": None,
        "queries": queries,
        "citations": [asdict(chunk) for chunk in evidence],
        "sources": [
            asdict(item.result) | {"canonical_url": item.canonical_url, "score": item.score, "source_label": item.source_label}
            for item in ranked
        ],
        "timings_ms": timings,
        "cache_hits": cache_hits,
        "fetcher_counts": fetcher_counts,
        "search_traces": [asdict(trace) for trace in search_traces],
        "provider_health": provider_health,
        "search_backend_status": search_backend_status,
        "weather_provider_status": weather_provider_status,
        "confidence": "medium" if fetched_count >= 3 else "low",
        "warnings": settings_warnings
        + _warnings(
            evidence,
            len(search_results),
            fetched_count,
            search_backend_status,
            weather_provider_status,
            fetcher_counts,
        ),
        "request_id": request_id,
        "config": config_status,
        "mode": profile.effective_mode,
        "requested_mode": profile.requested_mode,
        "freshness": effective_freshness,
        "requested_freshness": freshness,
        "answer_strategy": answer_strategy,
        "mode_profile": asdict(profile),
        "model": settings.lm_studio_model,
        "knowledge_prior": asdict(prior) if prior else None,
        "_evidence_chunks": evidence,
    }


async def answer_question(question: str, *, mode: str, freshness: str | None, settings: Settings) -> dict[str, object]:
    started = time.perf_counter()
    context = await collect_research_context(question, mode=mode, freshness=freshness, settings=settings)
    evidence = context.pop("_evidence_chunks")
    direct_answer = context.pop("direct_answer")

    if direct_answer is not None:
        context["answer"] = direct_answer
        return context

    profile = get_mode_profile(mode, settings)
    prior = get_knowledge_prior(question)

    if evidence:
        lm = LmStudioClient(
            settings.lm_studio_base_url,
            settings.lm_studio_api_key,
            settings.lm_studio_model,
            timeout_seconds=profile.synthesis_timeout_seconds,
            max_tokens=profile.lm_studio_max_tokens,
        )
        messages = build_answer_messages(question, evidence, prior, profile.answer_style)
        try:
            answer = await lm.chat(messages)
        except EmptyFinalContentError as exc:
            if not settings.lm_studio_retry_on_empty_content:
                answer = f"LM Studio synthesis failed after collecting web evidence: {exc}"
            else:
                try:
                    finalizer_messages = build_finalizer_messages(
                        question,
                        evidence[: min(5, len(evidence))],
                        prior,
                        profile.answer_style,
                    )
                    answer = await lm.chat(
                        finalizer_messages,
                        temperature=0.0,
                        max_tokens=profile.lm_studio_finalizer_max_tokens,
                    )
                except Exception as retry_exc:
                    retry_detail = str(retry_exc) or retry_exc.__class__.__name__
                    answer = (
                        "LM Studio synthesis failed after collecting web evidence: "
                        f"{exc}; finalizer retry failed: {retry_detail}"
                    )
        except Exception as exc:
            detail = str(exc) or exc.__class__.__name__
            answer = f"LM Studio synthesis failed after collecting web evidence: {detail}"
    else:
        answer = "I could not collect usable web evidence for this question."
    answer = cleanup_answer_for_prior(answer, question, prior)
    total_ms = int((time.perf_counter() - started) * 1000)
    timings = dict(context["timings_ms"])
    timings["synthesis"] = max(0, total_ms - int(timings["total"]))
    timings["total"] = total_ms
    validation = validate_answer(answer, evidence, prior)

    context.update({
        "answer": answer,
        "timings_ms": timings,
        "validation": validation.to_dict(),
    })
    return context
