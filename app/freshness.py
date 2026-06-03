from __future__ import annotations


_DAY_HINTS = (
    "today",
    "tonight",
    "now",
    "current",
    "weather",
    "forecast",
    "breaking",
    "right now",
    "오늘",
    "지금",
    "현재",
    "날씨",
    "예보",
    "속보",
)

_WEEK_HINTS = (
    "this week",
    "past week",
    "weekly",
    "이번 주",
    "이번주",
)

_MONTH_HINTS = (
    "latest",
    "recent",
    "newest",
    "updated",
    "release",
    "changelog",
    "version",
    "benchmark",
    "요즘",
    "최근",
    "최신",
    "업데이트",
    "릴리즈",
    "버전",
    "벤치마크",
)

_VALID_FRESHNESS = {"day", "week", "month", "year"}


def infer_freshness(question: str, requested: str | None) -> str | None:
    if requested in _VALID_FRESHNESS:
        return requested

    lowered = question.lower()
    if any(hint in lowered for hint in _DAY_HINTS):
        return "day"
    if any(hint in lowered for hint in _WEEK_HINTS):
        return "week"
    if any(hint in lowered for hint in _MONTH_HINTS):
        return "month"
    return None
