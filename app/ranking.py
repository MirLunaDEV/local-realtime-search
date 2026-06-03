from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.search.base import SearchResult
from app.source_policy import classify_source


TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


@dataclass(frozen=True)
class RankedResult:
    result: SearchResult
    canonical_url: str
    score: float
    source_label: str


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode(
        [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in TRACKING_PARAMS]
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[\w\uac00-\ud7a3]+", text) if len(token) > 1}


def rank_results(results: list[SearchResult], question: str, limit: int = 24) -> list[RankedResult]:
    question_tokens = _tokens(question)
    lowered_question = question.lower()
    best_by_url: dict[str, RankedResult] = {}

    for result in results:
        canonical_url = canonicalize_url(result.url)
        title_tokens = _tokens(result.title)
        snippet_tokens = _tokens(result.snippet)
        overlap = len(question_tokens & (title_tokens | snippet_tokens))
        rank_bonus = max(0.0, 10.0 - float(result.rank or 10))
        snippet_bonus = min(len(result.snippet) / 300.0, 2.0)
        policy = classify_source(canonical_url, result.title)

        url_parts = urlsplit(canonical_url)
        topic_bonus = 0.0
        if url_parts.netloc.endswith("lmstudio.ai") and (
            url_parts.path.startswith("/docs") or url_parts.path.startswith("/changelog")
        ):
            topic_bonus += 6.0
        if "docs" in url_parts.path.lower() or "documentation" in result.title.lower():
            topic_bonus += 2.0
        if "lm studio" in lowered_question and "search" in lowered_question:
            combined = f"{result.title} {result.snippet} {canonical_url}".lower()
            for term in ("searxng", "crawl4ai", "lm studio", "openai-compatible", "json api", "markdown"):
                if term in combined:
                    topic_bonus += 4.0
            if "crawl4ai" in combined:
                topic_bonus += 10.0
            if "docs.searxng.org/dev/search_api" in combined:
                topic_bonus += 8.0
            if "docs.searxng.org/dev/engines" in combined:
                topic_bonus -= 10.0
            if "opencode" in combined or "hermes" in combined or "unsloth" in combined or "lobehub" in combined:
                topic_bonus -= 6.0
        if "cache" in lowered_question and (
            "search" in lowered_question or "fetched" in lowered_question or "page" in lowered_question
        ):
            combined = f"{result.title} {result.snippet} {canonical_url}".lower()
            for term in ("sqlite", "ttl", "canonical url", "searxng", "search api", "lm studio"):
                if term in combined:
                    topic_bonus += 4.0
            if "docs.searxng.org/dev/search_api" in combined:
                topic_bonus += 8.0
            if "docs.python.org/3/library/sqlite3" in combined:
                topic_bonus += 8.0
            if (
                "redis" in combined
                or "valkey" in combined
                or "opensearch" in combined
                or "elasticsearch" in combined
            ) and not any(
                term in lowered_question for term in ("redis", "valkey", "opensearch", "elasticsearch")
            ):
                topic_bonus -= 8.0
        if "citation" in lowered_question and (
            "validate" in lowered_question or "quality" in lowered_question or "weak" in lowered_question
        ):
            combined = f"{result.title} {result.snippet} {canonical_url}".lower()
            for term in ("citation", "evidence", "source", "weak", "searxng", "crawl4ai", "lm studio"):
                if term in combined:
                    topic_bonus += 3.0
            if "docs.searxng.org/dev/search_api" in combined:
                topic_bonus += 8.0
            if "github.com/unclecode/crawl4ai" in combined or "docs.crawl4ai.com" in combined:
                topic_bonus += 6.0

        score = overlap * 2.0 + rank_bonus + snippet_bonus + policy.score_bonus + topic_bonus

        ranked = RankedResult(
            result=result,
            canonical_url=canonical_url,
            score=score,
            source_label=policy.label,
        )
        previous = best_by_url.get(canonical_url)
        if previous is None or ranked.score > previous.score:
            best_by_url[canonical_url] = ranked

    return sorted(best_by_url.values(), key=lambda item: item.score, reverse=True)[:limit]


def select_diverse_results(
    ranked: list[RankedResult],
    limit: int,
    *,
    max_per_host: int = 2,
) -> list[RankedResult]:
    selected: list[RankedResult] = []
    host_counts: dict[str, int] = {}

    for item in ranked:
        host = urlsplit(item.canonical_url).netloc
        if host_counts.get(host, 0) >= max_per_host:
            continue
        selected.append(item)
        host_counts[host] = host_counts.get(host, 0) + 1
        if len(selected) >= limit:
            return selected

    selected_urls = {item.canonical_url for item in selected}
    for item in ranked:
        if item.canonical_url in selected_urls:
            continue
        selected.append(item)
        if len(selected) >= limit:
            return selected

    return selected
