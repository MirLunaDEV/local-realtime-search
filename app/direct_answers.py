from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class DirectAnswer:
    answer: str
    label: str


_DATE_PATTERNS = (
    re.compile(r"\b(today|current date|what date|date today)\b", re.IGNORECASE),
    re.compile(r"(오늘|현재).*(날짜|며칠|몇\s*일|무슨\s*날)"),
    re.compile(r"(날짜|며칠|몇\s*일|무슨\s*날).*(오늘|현재)"),
)
_TIME_PATTERNS = (
    re.compile(r"\b(current time|what time|time now|what time is it)\b", re.IGNORECASE),
    re.compile(r"(지금|현재).*(시간|몇\s*시|몇시)"),
    re.compile(r"(시간|몇\s*시|몇시).*(지금|현재)"),
)
_KOREAN_RE = re.compile(r"[\u3131-\u318e\uac00-\ud7a3]")


def _zoneinfo(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def maybe_direct_answer(question: str, local_timezone: str) -> DirectAnswer | None:
    cleaned = " ".join(question.strip().split())
    if not cleaned:
        return None

    wants_date = any(pattern.search(cleaned) for pattern in _DATE_PATTERNS)
    wants_time = any(pattern.search(cleaned) for pattern in _TIME_PATTERNS)
    if not wants_date and not wants_time:
        return None

    try:
        tzinfo = _zoneinfo(local_timezone)
    except ZoneInfoNotFoundError:
        tzinfo = timezone.utc
        local_timezone = "UTC"
    now = datetime.now(tzinfo)
    is_korean = bool(_KOREAN_RE.search(cleaned))
    date_text = now.strftime("%Y-%m-%d")
    time_text = now.strftime("%H:%M:%S")
    weekday_en = now.strftime("%A")

    if wants_date and wants_time:
        if is_korean:
            return DirectAnswer(f"현재 날짜와 시간은 {date_text} {time_text} ({local_timezone})입니다.", "current_datetime")
        return DirectAnswer(f"The current date and time is {date_text} {time_text} ({local_timezone}).", "current_datetime")

    if wants_date:
        if is_korean:
            return DirectAnswer(f"오늘 날짜는 {date_text}입니다. 기준 시간대는 {local_timezone}입니다.", "current_date")
        return DirectAnswer(f"Today's date is {date_text} ({weekday_en}) in {local_timezone}.", "current_date")

    if is_korean:
        return DirectAnswer(f"현재 시간은 {time_text}입니다. 기준 시간대는 {local_timezone}입니다.", "current_time")
    return DirectAnswer(f"The current time is {time_text} in {local_timezone}.", "current_time")
