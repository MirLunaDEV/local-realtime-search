from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgePrior:
    label: str
    text: str


def get_knowledge_prior(question: str) -> KnowledgePrior | None:
    lowered = question.lower()
    local_stack_query = (
        (
            "lm studio" in lowered
            or "local llm" in lowered
            or "\ub85c\uceec" in question
        )
        and (
            "search" in lowered
            or "\uac80\uc0c9" in question
            or "\uc6f9\uac80\uc0c9" in question
        )
        and (
            "free" in lowered
            or "local" in lowered
            or "\ubb34\ub8cc" in question
            or "\ub85c\uceec" in question
        )
    )

    if local_stack_query:
        return KnowledgePrior(
            label="local_lm_studio_search_stack",
            text=(
                "Project prior for this question: the recommended free local-first stack is "
                "LM Studio as the local model runtime, SearXNG as the self-hosted metasearch/search API, "
                "Crawl4AI as the open-source page crawler/markdown extractor, SQLite cache for repeated "
                "search/page fetches, and a FastAPI orchestration layer for query planning, ranking, "
                "evidence selection, and answer synthesis. Treat web search as freshness/source validation. "
                "Do not replace this core stack with unrelated coding agents, MCP directories, social posts, "
                "or generic local-AI articles unless primary evidence clearly proves they are more relevant."
            ),
        )

    if "lm studio" in lowered and "tool" in lowered:
        return KnowledgePrior(
            label="lm_studio_tool_use",
            text=(
                "Project prior for this question: LM Studio tool use should be explained through its "
                "OpenAI-compatible local API, tool/function calling request flow, model loading/server mode, "
                "and official LM Studio developer documentation. Plugins and MCP are extensions, not the core API."
            ),
        )

    if "searxng" in lowered and "json" in lowered:
        return KnowledgePrior(
            label="searxng_json_api",
            text=(
                "Project prior for this question: SearXNG JSON output is requested with the query "
                "parameter format=json. For self-hosted instances, JSON must be allowed in settings.yml "
                "under search.formats, for example search: formats: [html, json]. Do not claim a "
                "[general] default_format: json setting unless official evidence explicitly supports it."
            ),
        )

    if "cache" in lowered and ("search" in lowered or "fetched" in lowered or "page" in lowered):
        return KnowledgePrior(
            label="local_search_cache_strategy",
            text=(
                "Project prior for this question: for this local realtime search assistant, use a small "
                "SQLite cache by default. Cache search results separately from fetched pages. Search-result "
                "cache keys should include provider, freshness, and normalized query, with a short TTL such "
                "as minutes. Page caches should be keyed by canonical URL and can use a longer TTL such as "
                "hours or a day. Keep cache metadata such as timestamps, provider, status, and source URL. "
                "Prefer SQLite for the default free local setup. If the user did not explicitly ask for "
                "scale-out architecture, do not name or recommend external cache services, search clusters, "
                "or vector indexes; just focus on the local SQLite design."
            ),
        )

    if "citation" in lowered and ("validate" in lowered or "quality" in lowered or "weak" in lowered):
        return KnowledgePrior(
            label="local_citation_quality",
            text=(
                "Project prior for this question: a web-grounded local LLM assistant should validate that "
                "every cited ID exists in the selected evidence, that cited sources are not weak social/video "
                "or generic commentary sources, and that required project-prior terms are present when a prior "
                "is active. Prefer official docs, GitHub primary repositories, government sites, release notes, "
                "and documentation. Keep warnings visible for thin evidence, snippet-only evidence, weak sources, "
                "and answer drift. Never let the model invent citation IDs or cite a source for unsupported claims."
            ),
        )

    return None
