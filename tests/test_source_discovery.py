import pytest

from app.search.source_discovery import OfficialModelHintsProvider, model_subject_from_query
from app.source_policy import classify_source


def test_model_subject_from_query_extracts_model_name() -> None:
    subject = model_subject_from_query("Gemma 4 12B latest benchmark scores MMLU GSM8K")

    assert subject == "Gemma 4 12B"


def test_model_subject_from_query_strips_research_tail_words() -> None:
    assert model_subject_from_query("Gemma 4 12B benchmark") == "Gemma 4 12B"
    assert model_subject_from_query("Gemma 4 12B GitHub issues") == "Gemma 4 12B"


@pytest.mark.anyio
async def test_official_model_hints_adds_gemma_sources() -> None:
    results = await OfficialModelHintsProvider().search("Gemma 4 12B benchmark")
    urls = {result.url for result in results}

    assert "https://ai.google.dev/gemma" in urls
    assert "https://ai.google.dev/gemma/docs" in urls
    assert "https://huggingface.co/models?search=Gemma+4+12B" in urls
    assert "https://github.com/search?q=Gemma+4+12B+benchmark&type=repositories" in urls


def test_source_policy_treats_huggingface_and_google_ai_as_primary() -> None:
    assert classify_source("https://huggingface.co/google/gemma-2-9b").is_primary is True
    assert classify_source("https://ai.google.dev/gemma/docs").is_primary is True
