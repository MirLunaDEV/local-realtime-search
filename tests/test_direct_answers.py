from app.config import Settings
from app.direct_answers import maybe_direct_answer
from app.pipeline import answer_question
import pytest


def test_maybe_direct_answer_handles_korean_today_date() -> None:
    answer = maybe_direct_answer("오늘 날짜가 뭐야?", "Asia/Seoul")

    assert answer is not None
    assert answer.label == "current_date"
    assert "오늘 날짜" in answer.answer
    assert "Asia/Seoul" in answer.answer


def test_maybe_direct_answer_handles_english_current_time() -> None:
    answer = maybe_direct_answer("What time is it now?", "UTC")

    assert answer is not None
    assert answer.label == "current_time"
    assert "UTC" in answer.answer


@pytest.mark.anyio
async def test_pipeline_returns_direct_date_without_search() -> None:
    response = await answer_question("오늘 날짜 알려줘", mode="fast", freshness=None, settings=Settings())

    assert response["confidence"] == "high"
    assert response["queries"] == []
    assert response["provider_health"] == []
    assert response["knowledge_prior"]["label"] == "current_date"
