from app.config import Settings


def test_default_model_is_explicit_not_auto() -> None:
    assert Settings().lm_studio_model == "qwen3.5-9b-uncensored-hauhaucs-aggressive"
