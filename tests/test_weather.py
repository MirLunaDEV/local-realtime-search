from app.weather import (
    WeatherEvidence,
    extract_weather_location,
    looks_weather_question,
    weather_payload_to_evidence,
)


def test_looks_weather_question_detects_korean_and_english() -> None:
    assert looks_weather_question("오늘 서울 날씨 알려줘")
    assert looks_weather_question("weather in Tokyo right now")
    assert not looks_weather_question("latest LM Studio MCP changes")
    assert not looks_weather_question("비교 분석")
    assert not looks_weather_question("2026년 6월 현재 생성형 AI 주요 동향과 성능 비교 분석")


def test_extract_weather_location_handles_common_patterns() -> None:
    assert extract_weather_location("오늘 서울 날씨 알려줘") == "Seoul,South Korea"
    assert extract_weather_location("weather in Tokyo right now") == "Tokyo"
    assert extract_weather_location("Busan forecast") == "Busan"


def test_weather_payload_to_evidence_builds_citation_ready_text() -> None:
    payload = {
        "nearest_area": [
            {
                "areaName": [{"value": "Seoul"}],
                "region": [{"value": "Seoul"}],
                "country": [{"value": "South Korea"}],
            }
        ],
        "current_condition": [
            {
                "localObsDateTime": "2026-06-04 10:00 AM",
                "weatherDesc": [{"value": "Partly cloudy"}],
                "temp_C": "24",
                "FeelsLikeC": "25",
                "humidity": "50",
                "precipMM": "0.0",
                "windspeedKmph": "9",
                "winddir16Point": "NW",
                "pressure": "1012",
                "visibility": "10",
            }
        ],
        "weather": [
            {
                "mintempC": "19",
                "maxtempC": "27",
                "avgtempC": "23",
                "astronomy": [{"sunrise": "05:12 AM", "sunset": "07:48 PM"}],
                "hourly": [{"chanceofrain": "10", "chanceofsnow": "0", "weatherDesc": [{"value": "Sunny"}]}] * 5,
            }
        ],
    }

    result = weather_payload_to_evidence(payload, "Seoul,South Korea")

    assert isinstance(result, WeatherEvidence)
    assert result.evidence.source_type == "weather"
    assert result.evidence.title == "Weather for Seoul,South Korea"
    assert "Nearest weather station/location: Seoul, Seoul, South Korea" in result.evidence.text
    assert "temperature 24C" in result.evidence.text
    assert result.source.url == "https://wttr.in/Seoul%2CSouth%20Korea?format=j1"
