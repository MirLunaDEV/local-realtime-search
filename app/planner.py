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
_BENCHMARK_HINTS = (
    "benchmark",
    "mmlu",
    "gsm8k",
    "humaneval",
    "math",
    "bbh",
    "\ubca4\uce58\ub9c8\ud06c",
    "\uc131\ub2a5 \ube44\uad50",
)
_MODEL_FAMILY_RE = re.compile(
    r"\b((?:gemma|qwen|llama|mistral|mixtral|phi|deepseek|yi|glm|gemini|gpt|claude)"
    r"(?:[\s\-]?[a-z0-9.]+){0,4}\s*(?:\d+\s*b)?)\b",
    re.IGNORECASE,
)
_INSTRUCTION_TAIL_RE = re.compile(
    r"\b(?:benchmark|scores?|mmlu|gsm8k|humaneval|math|bbh|model\s+card|hugging\s*face|reddit|community|"
    r"include|including|compare|comparison|review|reviews|with|and|especially|latest|updated|data)\b.*$",
    re.IGNORECASE,
)
_REQUEST_PREFIX_RE = re.compile(
    r"^(?:please|can you|could you|find|search for|look up|investigate|summarize|analyze|compare|tell me about)\s+",
    re.IGNORECASE,
)
_REQUEST_TOKEN_STOPWORDS = {
    "please",
    "find",
    "search",
    "look",
    "lookup",
    "investigate",
    "summarize",
    "analyze",
    "analysis",
    "detailed",
    "detail",
    "comprehensive",
    "report",
    "include",
    "including",
    "especially",
    "tell",
    "about",
    "with",
    "and",
    "the",
    "for",
    "in",
    "to",
    "fix",
    "how",
    "does",
    "should",
    "would",
    "could",
    "\uc0c1\uc138\ud788",
    "\uc790\uc138\ud788",
    "\uc870\uc0ac\ud574\uc918",
    "\uc54c\ub824\uc918",
    "\uc815\ub9ac\ud574\uc918",
    "\ubd84\uc11d\ud574\uc918",
    "\ube44\uad50\ud574\uc918",
    "\ud3ec\ud568\ud558\uc5ec",
    "\ud2b9\ud788",
}
_TROUBLESHOOTING_HINTS = (
    "error",
    "exception",
    "traceback",
    "failed",
    "cannot",
    "fix",
    "bug",
    "issue",
    "ModuleNotFoundError",
    "\uc624\ub958",
    "\uc5d0\ub7ec",
    "\ud574\uacb0",
)
_COMMUNITY_HINTS = (
    "reddit",
    "discord",
    "twitter",
    "x.com",
    "community",
    "review",
    "reviews",
    "github issues",
    "\ucee4\ubba4\ub2c8\ud2f0",
    "\ub9ac\ubdf0",
    "\ud6c4\uae30",
)
_DOCS_HINTS = (
    "docs",
    "documentation",
    "api",
    "changelog",
    "release notes",
    "official",
    "\ubb38\uc11c",
    "\uacf5\uc2dd",
    "\ub9b4\ub9ac\uc988",
)


def has_korean(text: str) -> bool:
    return bool(_KOREAN_RE.search(text))


def looks_current(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _CURRENT_HINTS)


def looks_benchmark_query(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _BENCHMARK_HINTS)


def _has_any_hint(text: str, hints: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(hint.lower() in lowered for hint in hints)


def _compact_model_name(question: str) -> str | None:
    match = _MODEL_FAMILY_RE.search(question)
    if not match:
        return None
    model = " ".join(match.group(1).split())
    model = _INSTRUCTION_TAIL_RE.sub("", model).strip(" ,-")
    return model or None


def _compact_general_query(question: str, *, max_terms: int = 14) -> str:
    normalized = _REQUEST_PREFIX_RE.sub("", question.strip())
    while True:
        stripped = _REQUEST_PREFIX_RE.sub("", normalized).strip()
        if stripped == normalized:
            break
        normalized = stripped
    raw_tokens = re.findall(r"[\w.+\-/\uac00-\ud7a3]+", normalized)
    tokens = [token.strip(".,:;!?()[]{}\"'") for token in raw_tokens]
    tokens = [token for token in tokens if token]
    filtered = [token for token in tokens if token.lower() not in _REQUEST_TOKEN_STOPWORDS]
    compact = " ".join((filtered or tokens)[:max_terms])
    if len(compact) > 110:
        compact = compact[:110].rsplit(" ", 1)[0] or compact[:110]
    return compact or question[:140]


def _generic_discovery_variants(question: str, base_query: str) -> list[str]:
    variants: list[str] = []
    if _has_any_hint(question, _DOCS_HINTS):
        variants.extend(
            [
                f"{base_query} official documentation",
                f"{base_query} release notes",
                f"site:github.com {base_query}",
            ]
        )
    if _has_any_hint(question, _TROUBLESHOOTING_HINTS):
        variants.extend(
            [
                f"{base_query} error fix",
                f"{base_query} GitHub issue",
                f"{base_query} Stack Overflow",
            ]
        )
    if _has_any_hint(question, _COMMUNITY_HINTS):
        variants.extend(
            [
                f"{base_query} Reddit review",
                f"{base_query} GitHub issues",
                f"{base_query} community discussion",
            ]
        )
    if " vs " in question.lower() or " versus " in question.lower() or "\ube44\uad50" in question:
        variants.extend(
            [
                f"{base_query} comparison",
                f"{base_query} alternatives",
            ]
        )
    if not variants:
        variants.extend(
            [
                f"{base_query} official",
                f"{base_query} documentation",
                f"{base_query} GitHub",
            ]
        )
    return variants


def _has_priority_generic_intent(question: str) -> bool:
    lowered = question.lower()
    return (
        _has_any_hint(question, _TROUBLESHOOTING_HINTS)
        or _has_any_hint(question, _COMMUNITY_HINTS)
        or " vs " in lowered
        or " versus " in lowered
        or "\ube44\uad50" in question
    )


def _benchmark_query_variants(question: str) -> list[str]:
    subject = _compact_model_name(question) or _compact_general_query(question, max_terms=8)
    return [
        f"{subject} benchmark",
        f"{subject} MMLU GSM8K HumanEval",
        f"{subject} model card",
        f"{subject} Hugging Face",
        f"{subject} Reddit review",
        f"site:ai.google.dev {subject}",
        f"site:developers.googleblog.com {subject}",
        f"site:huggingface.co {subject}",
    ]


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

    variants = _benchmark_query_variants(cleaned) if looks_benchmark_query(cleaned) else [_compact_general_query(cleaned)]
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

    if not looks_benchmark_query(cleaned) and _has_priority_generic_intent(cleaned):
        variants.extend(_generic_discovery_variants(cleaned, variants[0]))

    if current:
        variants.extend(
            [
                f"{variants[0]} latest",
                f"{variants[0]} news",
                f"{variants[0]} updated",
            ]
        )

    if has_korean(cleaned):
        variants.extend(
            [
                f"{variants[0]} release notes",
                f"{variants[0]} documentation",
                f"{variants[0]} \uacf5\uc2dd \ubb38\uc11c",
                f"{variants[0]} \ucd5c\uc2e0",
            ]
        )
    else:
        variants.extend(
            [
                f"{variants[0]} official documentation",
                f"{variants[0]} release notes",
            ]
        )

    if not looks_benchmark_query(cleaned) and not _has_priority_generic_intent(cleaned):
        variants.extend(_generic_discovery_variants(cleaned, variants[0]))

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
