from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class SourcePolicy:
    label: str
    score_bonus: float
    is_primary: bool = False
    is_weak: bool = False


OFFICIAL_HOSTS = {
    "lmstudio.ai",
    "www.lmstudio.ai",
    "docs.searxng.org",
    "docs.crawl4ai.com",
    "docs.python.org",
    "developer.mozilla.org",
}

WEAK_HOSTS = {
    "x.com",
    "twitter.com",
    "youtube.com",
    "www.youtube.com",
    "instagram.com",
    "www.instagram.com",
    "linkedin.com",
    "www.linkedin.com",
    "reddit.com",
    "www.reddit.com",
}


def classify_source(url: str, title: str = "") -> SourcePolicy:
    parts = urlsplit(url)
    host = parts.netloc.lower()
    path = parts.path.lower()
    lowered_title = title.lower()

    if host.endswith("wttr.in"):
        return SourcePolicy("weather_provider", 6.0, is_primary=True)
    if host in OFFICIAL_HOSTS:
        return SourcePolicy("official", 8.0, is_primary=True)
    if host.endswith(".gov") or host.endswith(".go.kr"):
        return SourcePolicy("government", 8.0, is_primary=True)
    if host == "github.com":
        if path.startswith("/unclecode/crawl4ai"):
            return SourcePolicy("github_primary", 8.0, is_primary=True)
        if "/issues/" in path or "/discussions/" in path:
            return SourcePolicy("github_discussion", 2.0)
        return SourcePolicy("github_primary", 5.0, is_primary=True)
    if host.startswith("docs.") or "docs" in path or "documentation" in lowered_title:
        return SourcePolicy("documentation", 4.0, is_primary=True)
    if "changelog" in path or "release" in path or "release notes" in lowered_title:
        return SourcePolicy("release_notes", 5.0, is_primary=True)
    if host in WEAK_HOSTS:
        return SourcePolicy("social_or_video", -2.0, is_weak=True)
    if "blog" in path or "review" in lowered_title:
        return SourcePolicy("commentary", -0.5)
    return SourcePolicy("general_web", 0.0)


def source_warning(url: str, title: str = "") -> str | None:
    policy = classify_source(url, title)
    if policy.is_weak:
        return f"Weak source included: {url}"
    if policy.label == "commentary":
        return f"Commentary source included: {url}"
    return None


def is_excluded_by_default(url: str, title: str = "") -> bool:
    policy = classify_source(url, title)
    return policy.is_weak or policy.label == "commentary"
