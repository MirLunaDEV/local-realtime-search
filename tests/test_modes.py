from app.config import Settings
from app.modes import get_mode_profile


def test_fast_profile_is_smaller_than_balanced() -> None:
    settings = Settings()
    fast = get_mode_profile("fast", settings)
    balanced = get_mode_profile("balanced", settings)

    assert fast.effective_mode == "fast"
    assert fast.max_evidence_chars < balanced.max_evidence_chars
    assert fast.lm_studio_max_tokens < balanced.lm_studio_max_tokens


def test_deep_profile_is_larger_than_balanced() -> None:
    settings = Settings()
    deep = get_mode_profile("deep", settings)
    balanced = get_mode_profile("balanced", settings)

    assert deep.effective_mode == "deep"
    assert deep.max_fetch_urls > balanced.max_fetch_urls
    assert deep.lm_studio_max_tokens > balanced.lm_studio_max_tokens


def test_unknown_mode_falls_back_to_fast() -> None:
    profile = get_mode_profile("turbo", Settings())

    assert profile.requested_mode == "turbo"
    assert profile.effective_mode == "fast"
