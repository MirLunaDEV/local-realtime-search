from app.source_policy import classify_source, is_excluded_by_default, source_warning


def test_classify_official_docs() -> None:
    policy = classify_source("https://lmstudio.ai/docs/developer/openai-compat/tools")

    assert policy.label == "official"
    assert policy.is_primary
    assert policy.score_bonus > 0


def test_classify_social_as_weak() -> None:
    policy = classify_source("https://x.com/example/status/1")

    assert policy.is_weak
    assert policy.score_bonus < 0


def test_classify_crawl4ai_repo_as_primary() -> None:
    policy = classify_source("https://github.com/unclecode/crawl4ai")

    assert policy.is_primary
    assert policy.score_bonus >= 8.0


def test_source_warning_for_weak_source() -> None:
    assert source_warning("https://www.instagram.com/p/example") is not None


def test_default_exclusion_for_commentary_and_social() -> None:
    assert is_excluded_by_default("https://www.instagram.com/p/example")
    assert is_excluded_by_default("https://example.com/blog/review")
    assert not is_excluded_by_default("https://docs.searxng.org/dev/search_api.html")
