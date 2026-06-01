from __future__ import annotations

import os
from dataclasses import dataclass


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    lm_studio_base_url: str = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
    lm_studio_api_key: str = os.getenv("LM_STUDIO_API_KEY", "lm-studio")
    lm_studio_model: str = os.getenv("LM_STUDIO_MODEL", "your-loaded-lm-studio-model-id")
    local_timezone: str = os.getenv("LOCAL_TIMEZONE", "Asia/Seoul")
    searxng_base_url: str = os.getenv("SEARXNG_BASE_URL", "http://127.0.0.1:8080")
    cache_path: str = os.getenv("CACHE_PATH", ".cache/local-realtime-search.sqlite3")
    search_cache_ttl_seconds: int = _int_env("SEARCH_CACHE_TTL_SECONDS", 900)
    page_cache_ttl_seconds: int = _int_env("PAGE_CACHE_TTL_SECONDS", 86400)
    fetcher: str = os.getenv("FETCHER", "auto")
    lm_studio_max_tokens: int = _int_env("LM_STUDIO_MAX_TOKENS", 4096)
    lm_studio_finalizer_max_tokens: int = _int_env("LM_STUDIO_FINALIZER_MAX_TOKENS", 2048)
    lm_studio_retry_on_empty_content: bool = os.getenv("LM_STUDIO_RETRY_ON_EMPTY_CONTENT", "true").lower() == "true"
    search_timeout_seconds: float = _float_env("SEARCH_TIMEOUT_SECONDS", 2.5)
    fetch_timeout_seconds: float = _float_env("FETCH_TIMEOUT_SECONDS", 3.0)
    crawl4ai_timeout_seconds: float = _float_env("CRAWL4AI_TIMEOUT_SECONDS", 8.0)
    synthesis_timeout_seconds: float = _float_env("SYNTHESIS_TIMEOUT_SECONDS", 180.0)
    max_query_variants: int = _int_env("MAX_QUERY_VARIANTS", 6)
    max_candidate_urls: int = _int_env("MAX_CANDIDATE_URLS", 24)
    max_fetch_urls: int = _int_env("MAX_FETCH_URLS", 16)
    max_evidence_chunks: int = _int_env("MAX_EVIDENCE_CHUNKS", 20)
    max_evidence_chars: int = _int_env("MAX_EVIDENCE_CHARS", 24000)


def get_settings() -> Settings:
    return Settings()
