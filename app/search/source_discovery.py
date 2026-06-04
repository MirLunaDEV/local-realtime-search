from __future__ import annotations

import re
from urllib.parse import quote_plus

import httpx

from app.search.base import SearchResult


_MODEL_RE = re.compile(
    r"\b((?:gemma|qwen|llama|mistral|mixtral|phi|deepseek|yi|glm|gemini|gpt|claude)"
    r"(?:[\s\-]?[a-z0-9.]+){0,4}\s*(?:\d+\s*b)?)\b",
    re.IGNORECASE,
)
_SUBJECT_TAIL_RE = re.compile(
    r"\b(?:benchmark|scores?|mmlu|gsm8k|humaneval|math|bbh|model\s+card|hugging\s*face|reddit|review|"
    r"latest|updated|community|comparison|analysis)\b.*$",
    re.IGNORECASE,
)
_SUBJECT_STOP_WORDS = {
    "analysis",
    "benchmark",
    "benchmarks",
    "bbh",
    "card",
    "community",
    "comparison",
    "discord",
    "docs",
    "documentation",
    "eval",
    "evaluation",
    "github",
    "gsm8k",
    "huggingface",
    "humaneval",
    "issue",
    "issues",
    "latest",
    "math",
    "mmlu",
    "modelcard",
    "reddit",
    "review",
    "reviews",
    "score",
    "scores",
    "twitter",
    "updated",
}


def _strip_subject_tail(subject: str) -> str:
    subject = _SUBJECT_TAIL_RE.sub("", subject).strip(" ,-")
    parts: list[str] = []
    for part in subject.split():
        normalized = re.sub(r"[^a-z0-9]+", "", part.lower())
        if normalized in _SUBJECT_STOP_WORDS:
            break
        parts.append(part)
    return " ".join(parts).strip(" ,-")


def model_subject_from_query(query: str) -> str | None:
    match = _MODEL_RE.search(query)
    if not match:
        return None
    subject = _strip_subject_tail(" ".join(match.group(1).split()).strip(" ,-"))
    return subject or None


class OfficialModelHintsProvider:
    name = "official_model_hints"

    async def search(self, query: str, *, freshness: str | None = None, limit: int = 10) -> list[SearchResult]:
        lowered = query.lower()
        subject = model_subject_from_query(query)
        results: list[SearchResult] = []

        if "gemma" in lowered:
            results.extend(
                [
                    SearchResult(
                        title="Gemma - Google AI for Developers",
                        url="https://ai.google.dev/gemma",
                        snippet="Google's official Gemma page for model families, downloads, docs, and developer resources.",
                        provider=self.name,
                        rank=1,
                    ),
                    SearchResult(
                        title="Gemma Documentation - Google AI for Developers",
                        url="https://ai.google.dev/gemma/docs",
                        snippet="Official Gemma documentation from Google AI for Developers.",
                        provider=self.name,
                        rank=2,
                    ),
                    SearchResult(
                        title="Google Developers Blog search for Gemma",
                        url="https://developers.googleblog.com/search/?q=Gemma",
                        snippet="Google Developers Blog search results for Gemma announcements and updates.",
                        provider=self.name,
                        rank=3,
                    ),
                ]
            )

        if subject:
            encoded = quote_plus(subject)
            results.extend(
                [
                    SearchResult(
                        title=f"Hugging Face model search for {subject}",
                        url=f"https://huggingface.co/models?search={encoded}",
                        snippet=f"Hugging Face model search page for {subject}, useful for model cards and community uploads.",
                        provider=self.name,
                        rank=len(results) + 1,
                    ),
                    SearchResult(
                        title=f"GitHub repository search for {subject}",
                        url=f"https://github.com/search?q={encoded}+benchmark&type=repositories",
                        snippet=f"GitHub repository search for {subject} benchmark implementations, evaluations, and tooling.",
                        provider=self.name,
                        rank=len(results) + 2,
                    ),
                ]
            )

        return results[:limit]


class HuggingFaceModelsProvider:
    name = "huggingface_models"

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._cache: dict[tuple[str, int], list[SearchResult]] = {}

    async def search(self, query: str, *, freshness: str | None = None, limit: int = 10) -> list[SearchResult]:
        subject = model_subject_from_query(query)
        if subject is None:
            return []
        result_limit = min(max(limit, 1), 25)
        cache_key = (subject.lower(), result_limit)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return list(cached)[:result_limit]

        params = {
            "search": subject,
            "limit": result_limit,
            "sort": "downloads",
            "direction": "-1",
        }
        headers = {"user-agent": "local-realtime-search/0.1"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers, follow_redirects=True) as client:
            response = await client.get("https://huggingface.co/api/models", params=params)
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, list):
            return []

        results: list[SearchResult] = []
        for index, item in enumerate(payload[:limit], start=1):
            if not isinstance(item, dict):
                continue
            model_id = str(item.get("modelId") or item.get("id") or "").strip()
            if not model_id:
                continue
            downloads = item.get("downloads")
            likes = item.get("likes")
            pipeline_tag = item.get("pipeline_tag") or "model"
            last_modified = item.get("lastModified")
            results.append(
                SearchResult(
                    title=f"Hugging Face model: {model_id}",
                    url=f"https://huggingface.co/{model_id}",
                    snippet=(
                        f"Hugging Face {pipeline_tag}; downloads={downloads or 0}; likes={likes or 0}. "
                        "Open the model card for details, files, community comments, and evaluation notes."
                    ),
                    provider=self.name,
                    rank=index,
                    published_or_updated=str(last_modified) if last_modified else None,
                )
            )
        self._cache[cache_key] = results
        return list(results)


class GitHubRepositoryProvider:
    name = "github_repositories"

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._cache: dict[tuple[str, int], list[SearchResult]] = {}

    async def search(self, query: str, *, freshness: str | None = None, limit: int = 10) -> list[SearchResult]:
        subject = model_subject_from_query(query)
        if subject is None:
            return []
        result_limit = min(max(limit, 1), 20)
        cache_key = (subject.lower(), result_limit)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return list(cached)[:result_limit]

        params = {
            "q": f"{subject} benchmark OR eval OR evaluation",
            "per_page": result_limit,
            "sort": "updated",
            "order": "desc",
        }
        headers = {
            "accept": "application/vnd.github+json",
            "user-agent": "local-realtime-search/0.1",
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers, follow_redirects=True) as client:
            response = await client.get("https://api.github.com/search/repositories", params=params)
            response.raise_for_status()
            payload = response.json()

        items = payload.get("items", []) if isinstance(payload, dict) else []
        if not isinstance(items, list):
            return []

        results: list[SearchResult] = []
        for index, item in enumerate(items[:limit], start=1):
            if not isinstance(item, dict):
                continue
            html_url = str(item.get("html_url") or "").strip()
            full_name = str(item.get("full_name") or html_url).strip()
            if not html_url:
                continue
            description = str(item.get("description") or "")
            stars = item.get("stargazers_count")
            updated = item.get("updated_at")
            results.append(
                SearchResult(
                    title=f"GitHub repository: {full_name}",
                    url=html_url,
                    snippet=f"{description} Stars={stars or 0}. Updated={updated or 'unknown'}.",
                    provider=self.name,
                    rank=index,
                    published_or_updated=str(updated) if updated else None,
                )
            )
        self._cache[cache_key] = results
        return list(results)
