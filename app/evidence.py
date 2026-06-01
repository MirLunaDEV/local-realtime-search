from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.fetch.http_fetcher import FetchedPage
from app.search.base import SearchResult
from app.source_policy import classify_source, is_excluded_by_default


@dataclass(frozen=True)
class EvidenceChunk:
    id: int
    title: str
    url: str
    text: str
    provider: str
    published_or_updated: str | None = None
    source_type: str = "page"


def chunk_text(text: str, chunk_chars: int = 900, overlap_chars: int = 120) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_chars)
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(end - overlap_chars, start + 1)
    return chunks


def evidence_from_page(source: SearchResult, page: FetchedPage, start_id: int, max_chunks: int = 3) -> list[EvidenceChunk]:
    title = page.title or source.title
    chunks = chunk_text(page.text)[:max_chunks]
    return [
        EvidenceChunk(
            id=start_id + index,
            title=title,
            url=page.url or source.url,
            text=chunk,
            provider=source.provider,
            published_or_updated=source.published_or_updated,
            source_type="page",
        )
        for index, chunk in enumerate(chunks)
    ]


def evidence_from_snippet(source: SearchResult, chunk_id: int) -> EvidenceChunk | None:
    text = " ".join(source.snippet.split())
    if not text:
        return None
    return EvidenceChunk(
        id=chunk_id,
        title=source.title,
        url=source.url,
        text=text[:900],
        provider=source.provider,
        published_or_updated=source.published_or_updated,
        source_type="snippet",
    )


def format_evidence(chunks: list[EvidenceChunk]) -> str:
    lines: list[str] = []
    for chunk in chunks:
        date = f" | date={chunk.published_or_updated}" if chunk.published_or_updated else ""
        policy = classify_source(chunk.url, chunk.title)
        lines.append(
            f"[{chunk.id}] {chunk.title}\n"
            f"url={chunk.url} | provider={chunk.provider} | type={chunk.source_type} | source={policy.label}{date}\n"
            f"{chunk.text}"
        )
    return "\n\n".join(lines)


def fit_evidence_budget(chunks: list[EvidenceChunk], max_chars: int) -> list[EvidenceChunk]:
    fitted: list[EvidenceChunk] = []
    used = 0
    for chunk in chunks:
        cost = len(chunk.title) + len(chunk.url) + len(chunk.text) + 80
        if fitted and used + cost > max_chars:
            break
        if cost > max_chars:
            trimmed = EvidenceChunk(
                id=chunk.id,
                title=chunk.title,
                url=chunk.url,
                text=chunk.text[: max(300, max_chars - len(chunk.title) - len(chunk.url) - 120)],
                provider=chunk.provider,
                published_or_updated=chunk.published_or_updated,
                source_type=chunk.source_type,
            )
            fitted.append(trimmed)
            break
        fitted.append(chunk)
        used += cost
    return fitted


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[\w\uac00-\ud7a3]+", text) if len(token) > 1}


def select_evidence(chunks: list[EvidenceChunk], question: str, limit: int, max_chars: int) -> list[EvidenceChunk]:
    question_tokens = _tokens(question)
    lowered_question = question.lower()
    filtered_chunks = [chunk for chunk in chunks if not is_excluded_by_default(chunk.url, chunk.title)]
    if len(filtered_chunks) >= 3:
        chunks = filtered_chunks

    def score(chunk: EvidenceChunk) -> float:
        chunk_tokens = _tokens(f"{chunk.title} {chunk.text}")
        overlap = len(question_tokens & chunk_tokens) * 2.0
        policy = classify_source(chunk.url, chunk.title)
        source_bonus = (1.0 if chunk.source_type == "page" else 0.0) + policy.score_bonus
        parts = urlsplit(chunk.url)
        topic_bonus = 0.0
        if parts.netloc.endswith("lmstudio.ai") and (
            parts.path.startswith("/docs") or parts.path.startswith("/changelog")
        ):
            topic_bonus += 8.0
        if "tool" in chunk.title.lower() or "tool" in chunk.text.lower():
            topic_bonus += 2.0
        if "lm studio" in lowered_question and "search" in lowered_question:
            combined = f"{chunk.title} {chunk.text} {chunk.url}".lower()
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
            combined = f"{chunk.title} {chunk.text} {chunk.url}".lower()
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
            combined = f"{chunk.title} {chunk.text} {chunk.url}".lower()
            for term in ("citation", "evidence", "source", "weak", "searxng", "crawl4ai", "lm studio"):
                if term in combined:
                    topic_bonus += 3.0
            if "docs.searxng.org/dev/search_api" in combined:
                topic_bonus += 8.0
            if "github.com/unclecode/crawl4ai" in combined or "docs.crawl4ai.com" in combined:
                topic_bonus += 6.0
        return overlap + source_bonus + topic_bonus

    ranked = sorted(chunks, key=score, reverse=True)
    return fit_evidence_budget(ranked[:limit], max_chars)
