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
    "\ucee4\ubba4\ub2c8\ud2f0",
)
_MODEL_FAMILY_RE = re.compile(
    r"\b((?:gemma|qwen|llama|mistral|mixtral|phi|deepseek|yi|glm|gemini|gpt|claude)"
    r"(?:[\s\-]?[a-z0-9.]+){0,4}\s*(?:\d+\s*b)?)\b",
    re.IGNORECASE,
)
_INSTRUCTION_TAIL_RE = re.compile(
    r"\b(?:include|including|compare|comparison|review|reviews|with|and|especially|latest|updated|data)\b.*$",
    re.IGNORECASE,
)


def has_korean(text: str) -> bool:
    return bool(_KOREAN_RE.search(text))


def looks_current(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _CURRENT_HINTS)


def looks_benchmark_query(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _BENCHMARK_HINTS)


def _compact_model_name(question: str) -> str | None:
    match = _MODEL_FAMILY_RE.search(question)
    if not match:
        return None
    model = " ".join(match.group(1).split())
    model = _INSTRUCTION_TAIL_RE.sub("", model).strip(" ,-")
    return model or None


def _compact_general_query(question: str, *, max_terms: int = 12) -> str:
    tokens = re.findall(r"[\w.+\-/\uac00-\ud7a3]+", question)
    compact = " ".join(tokens[:max_terms])
    return compact or question[:140]


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
