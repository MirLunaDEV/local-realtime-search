from __future__ import annotations

import re


_KOREAN_RE = re.compile(r"[\u3131-\u318e\uac00-\ud7a3]")
_CURRENT_HINTS = (
    "latest",
    "recent",
    "today",
    "now",
    "\ud604\uc7ac",
    "\ucd5c\uc2e0",
    "\uc694\uc998",
    "\uc624\ub298",
    "\ucd5c\uadfc",
)


def has_korean(text: str) -> bool:
    return bool(_KOREAN_RE.search(text))


def looks_current(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _CURRENT_HINTS)


def is_local_search_stack_query(text: str) -> bool:
    lowered = text.lower()
    return (
        (
            "lm studio" in lowered
            or "local llm" in lowered
            or "\ub85c\uceec" in text
        )
        and (
            "search" in lowered
            or "\uac80\uc0c9" in text
            or "\uc6f9\uac80\uc0c9" in text
        )
        and (
            "free" in lowered
            or "local" in lowered
            or "\ubb34\ub8cc" in text
            or "\ub85c\uceec" in text
        )
    )


def plan_queries(question: str, max_queries: int = 6, freshness: str | None = None) -> list[str]:
    cleaned = " ".join(question.strip().split())
    if not cleaned:
        return []

    variants = [cleaned]
    current = looks_current(cleaned) or freshness in {"day", "week", "month"}
    lowered = cleaned.lower()

    if "lm studio" in lowered and "tool" in lowered:
        variants.extend(
            [
                "site:lmstudio.ai/docs LM Studio tool use",
                "site:lmstudio.ai/docs LM Studio OpenAI compatible tools",
                "LM Studio tool use official documentation",
            ]
        )

    if is_local_search_stack_query(cleaned):
        variants.extend(
            [
                "SearXNG Crawl4AI LM Studio local web search stack",
                "site:docs.searxng.org SearXNG search API JSON format",
                "site:docs.crawl4ai.com Crawl4AI markdown LLM extraction",
                "github unclecode crawl4ai open source LLM web crawler",
                "LM Studio OpenAI compatible API local server docs",
            ]
        )

    if "cache" in lowered and ("search" in lowered or "fetched" in lowered or "page" in lowered):
        variants.extend(
            [
                "SearXNG search API cache local assistant SQLite TTL",
                "SQLite cache strategy local web search assistant canonical URL TTL",
                "site:docs.searxng.org SearXNG search API results cache",
                "github local web search assistant SQLite cache citations",
            ]
        )

    if "citation" in lowered and ("validate" in lowered or "quality" in lowered or "weak" in lowered):
        variants.extend(
            [
                "web grounded LLM citation validation weak sources evidence IDs",
                "local LLM web search citation validator official sources",
                "github citation validation web grounded LLM assistant",
                "site:docs.searxng.org search API citations sources",
            ]
        )

    if current:
        variants.extend(
            [
                f"{cleaned} latest",
                f"{cleaned} news",
                f"{cleaned} updated",
            ]
        )

    if has_korean(cleaned):
        variants.extend(
            [
                f"{cleaned} release notes",
                f"{cleaned} documentation",
                f"{cleaned} \uacf5\uc2dd \ubb38\uc11c",
                f"{cleaned} \ucd5c\uc2e0",
            ]
        )
    else:
        variants.extend(
            [
                f"{cleaned} official documentation",
                f"{cleaned} release notes",
            ]
        )

    deduped: list[str] = []
    seen: set[str] = set()
    for variant in variants:
        key = variant.lower()
        if key not in seen:
            deduped.append(variant)
            seen.add(key)
        if len(deduped) >= max_queries:
            break
    return deduped
