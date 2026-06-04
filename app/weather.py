from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from urllib.parse import quote

import httpx

from app.evidence import EvidenceChunk
from app.search.base import SearchResult


_WEATHER_HINTS = (
    "weather",
    "forecast",
    "temperature",
    "rain",
    "snow",
    "날씨",
    "예보",
    "기온",
    "비",
    "눈",
)

_STRONG_WEATHER_HINTS = (
    "weather",
    "forecast",
    "temperature",
    "\ub0a0\uc528",
    "\uc608\ubcf4",
    "\uae30\uc628",
    "\uac15\uc218",
)

_WEATHER_EVENT_PATTERNS = (
    r"\brain\b",
    r"\bsnow\b",
    r"(?<![\uac00-\ud7a3])\ube44(?![\uac00-\ud7a3])",
    r"(?<![\uac00-\ud7a3])\ub208(?![\uac00-\ud7a3])",
    r"\ube44\s*(?:\uc640|\uc624|\uc62c|\ub0b4)",
    r"\ub208\s*(?:\uc640|\uc624|\uc62c|\ub0b4)",
)

_LOCATION_ALIASES = {
    "서울": "Seoul,South Korea",
    "부산": "Busan,South Korea",
    "인천": "Incheon,South Korea",
    "대구": "Daegu,South Korea",
    "대전": "Daejeon,South Korea",
    "광주": "Gwangju,South Korea",
    "울산": "Ulsan,South Korea",
    "제주": "Jeju,South Korea",
    "도쿄": "Tokyo,Japan",
    "오사카": "Osaka,Japan",
    "뉴욕": "New York,United States",
    "런던": "London,United Kingdom",
}

_KOREAN_FILLERS = (
    "오늘",
    "내일",
    "모레",
    "현재",
    "지금",
    "이번 주",
    "이번주",
    "날씨",
    "예보",
    "알려줘",
    "어때",
    "비",
    "눈",
    "오나",
    "와",
)


@dataclass(frozen=True)
class WeatherProviderStatus:
    provider: str
    status: str
    location: str | None
    elapsed_ms: int
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class WeatherEvidence:
    evidence: EvidenceChunk
    source: SearchResult
    status: WeatherProviderStatus


def looks_weather_question(question: str) -> bool:
    lowered = question.lower()
    if any(hint in lowered for hint in _STRONG_WEATHER_HINTS):
        return True
    return any(re.search(pattern, question, re.IGNORECASE) for pattern in _WEATHER_EVENT_PATTERNS)


def extract_weather_location(question: str) -> str | None:
    for korean, english in _LOCATION_ALIASES.items():
        if korean in question:
            return english

    lowered = question.lower()
    patterns = (
        r"(?:weather|forecast|temperature)\s+(?:in|for|at)\s+([a-zA-Z][a-zA-Z\s.'-]{1,50})",
        r"([a-zA-Z][a-zA-Z\s.'-]{1,50})\s+(?:weather|forecast|temperature)",
    )
    for pattern in patterns:
        match = re.search(pattern, lowered, re.IGNORECASE)
        if match:
            return _clean_location(match.group(1))

    korean_match = re.search(r"([\uac00-\ud7a3A-Za-z\s]{2,40})\s*(?:날씨|예보)", question)
    if korean_match:
        candidate = korean_match.group(1)
        for filler in _KOREAN_FILLERS:
            candidate = candidate.replace(filler, " ")
        return _clean_location(candidate)
    return None


def _clean_location(value: str) -> str | None:
    cleaned = " ".join(value.replace("?", " ").replace(",", " ").split())
    cleaned = re.sub(r"\b(today|tomorrow|tonight|now|current|right|please|tell me|the)\b", " ", cleaned, flags=re.I)
    cleaned = " ".join(cleaned.split()).strip(" .'-")
    if not cleaned:
        return None
    if re.fullmatch(r"[a-zA-Z\s.'-]+", cleaned):
        return cleaned.title()
    return cleaned


def _first_text(value: object) -> str:
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return str(first.get("value") or "")
    return ""


def _forecast_line(day: dict[str, object], label: str) -> str:
    astronomy = (day.get("astronomy") or [{}])[0]
    hourly = (day.get("hourly") or [{}])[4]
    chance_of_rain = hourly.get("chanceofrain", "unknown")
    chance_of_snow = hourly.get("chanceofsnow", "unknown")
    description = _first_text(hourly.get("weatherDesc"))
    return (
        f"{label}: {description}; min {day.get('mintempC')}C, max {day.get('maxtempC')}C, "
        f"avg {day.get('avgtempC')}C, rain chance {chance_of_rain}%, snow chance {chance_of_snow}%, "
        f"sunrise {astronomy.get('sunrise')}, sunset {astronomy.get('sunset')}."
    )


def weather_payload_to_evidence(payload: dict[str, object], location: str, *, chunk_id: int = 1) -> WeatherEvidence:
    current = (payload.get("current_condition") or [{}])[0]
    nearest_area = (payload.get("nearest_area") or [{}])[0]
    area_name = _first_text(nearest_area.get("areaName")) or location
    country = _first_text(nearest_area.get("country"))
    region = _first_text(nearest_area.get("region"))
    resolved = ", ".join(part for part in (area_name, region, country) if part)
    weather_days = payload.get("weather") or []
    forecast_lines = [
        _forecast_line(day, "Today" if index == 0 else "Tomorrow")
        for index, day in enumerate(weather_days[:2])
        if isinstance(day, dict)
    ]
    description = _first_text(current.get("weatherDesc"))
    observed = str(current.get("localObsDateTime") or current.get("observation_time") or "")
    url = f"https://wttr.in/{quote(location)}?format=j1"
    text = (
        f"Requested location: {location}. Nearest weather station/location: {resolved or location}. "
        f"Observed: {observed}. "
        f"Current: {description}; temperature {current.get('temp_C')}C, feels like {current.get('FeelsLikeC')}C, "
        f"humidity {current.get('humidity')}%, precipitation {current.get('precipMM')}mm, "
        f"wind {current.get('windspeedKmph')} km/h {current.get('winddir16Point')}, "
        f"pressure {current.get('pressure')} hPa, visibility {current.get('visibility')} km. "
        + " ".join(forecast_lines)
    )
    title = f"Weather for {location}"
    source = SearchResult(
        title=title,
        url=url,
        snippet=text[:900],
        provider="wttr_in",
        rank=1,
        published_or_updated=observed or None,
    )
    evidence = EvidenceChunk(
        id=chunk_id,
        title=title,
        url=url,
        text=text,
        provider="wttr_in",
        published_or_updated=observed or None,
        source_type="weather",
    )
    return WeatherEvidence(
        evidence=evidence,
        source=source,
        status=WeatherProviderStatus(
            provider="wttr_in",
            status="ok",
            location=location,
            elapsed_ms=0,
        ),
    )


async def collect_weather_evidence(question: str, *, timeout_seconds: float) -> WeatherEvidence | WeatherProviderStatus:
    started = time.perf_counter()
    if not looks_weather_question(question):
        return WeatherProviderStatus("wttr_in", "not_used", None, 0, "Question does not look like weather.")

    location = extract_weather_location(question)
    if location is None:
        return WeatherProviderStatus(
            "wttr_in",
            "skipped",
            None,
            int((time.perf_counter() - started) * 1000),
            "Could not infer a weather location from the question.",
        )

    url = f"https://wttr.in/{quote(location)}"
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url, params={"format": "j1"})
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        return WeatherProviderStatus(
            "wttr_in",
            "down",
            location,
            int((time.perf_counter() - started) * 1000),
            (str(exc) or exc.__class__.__name__)[:300],
        )

    result = weather_payload_to_evidence(payload, location)
    return WeatherEvidence(
        evidence=result.evidence,
        source=result.source,
        status=WeatherProviderStatus(
            "wttr_in",
            "ok",
            location,
            int((time.perf_counter() - started) * 1000),
        ),
    )
