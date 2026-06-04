from __future__ import annotations

from dataclasses import asdict, dataclass
from urllib.parse import urlsplit

from app.config import Settings


@dataclass(frozen=True)
class ConfigIssue:
    severity: str
    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _valid_http_url(value: str) -> bool:
    parts = urlsplit(value)
    return parts.scheme in {"http", "https"} and bool(parts.netloc)


def validate_settings(settings: Settings) -> dict[str, object]:
    issues: list[ConfigIssue] = []

    if settings.lm_studio_model == "your-loaded-lm-studio-model-id":
        issues.append(
            ConfigIssue(
                "warning",
                "LM_STUDIO_MODEL",
                "LM Studio model is still the placeholder value; this only affects /ask API synthesis, not the LM Studio MCP tool result.",
            )
        )
    if not _valid_http_url(settings.lm_studio_base_url):
        issues.append(ConfigIssue("error", "LM_STUDIO_BASE_URL", "LM Studio base URL must be an http(s) URL."))
    if not _valid_http_url(settings.searxng_base_url):
        issues.append(ConfigIssue("error", "SEARXNG_BASE_URL", "SearXNG base URL must be an http(s) URL."))
    if settings.fetcher not in {"auto", "http", "crawl4ai"}:
        issues.append(ConfigIssue("error", "FETCHER", "FETCHER must be one of auto, http, or crawl4ai."))

    numeric_fields = {
        "SEARCH_TIMEOUT_SECONDS": settings.search_timeout_seconds,
        "WEATHER_TIMEOUT_SECONDS": settings.weather_timeout_seconds,
        "FETCH_TIMEOUT_SECONDS": settings.fetch_timeout_seconds,
        "CRAWL4AI_TIMEOUT_SECONDS": settings.crawl4ai_timeout_seconds,
        "SYNTHESIS_TIMEOUT_SECONDS": settings.synthesis_timeout_seconds,
        "MAX_QUERY_VARIANTS": settings.max_query_variants,
        "MAX_CANDIDATE_URLS": settings.max_candidate_urls,
        "MAX_FETCH_URLS": settings.max_fetch_urls,
        "MAX_EVIDENCE_CHUNKS": settings.max_evidence_chunks,
        "MAX_EVIDENCE_CHARS": settings.max_evidence_chars,
    }
    for field, value in numeric_fields.items():
        if value <= 0:
            issues.append(ConfigIssue("error", field, f"{field} must be greater than 0."))

    if settings.allow_private_network_fetch:
        issues.append(
            ConfigIssue(
                "warning",
                "ALLOW_PRIVATE_NETWORK_FETCH",
                "Private/internal network fetching is enabled; this reduces SSRF protection.",
            )
        )
    if not settings.resolve_fetch_hostnames:
        issues.append(
            ConfigIssue(
                "warning",
                "RESOLVE_FETCH_HOSTNAMES",
                "Hostname resolution safety checks are disabled; private-network DNS targets may not be detected.",
            )
        )

    status = "ok"
    if any(issue.severity == "error" for issue in issues):
        status = "error"
    elif issues:
        status = "warning"

    return {
        "status": status,
        "issues": [issue.to_dict() for issue in issues],
    }


def config_warnings(config_status: dict[str, object]) -> list[str]:
    issues = config_status.get("issues", [])
    warnings: list[str] = []
    if isinstance(issues, list):
        for item in issues:
            if isinstance(item, dict):
                message = item.get("message")
                field = item.get("field")
                if message and field:
                    warnings.append(f"Config {field}: {message}")
    return warnings
