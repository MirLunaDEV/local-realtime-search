from app.config import Settings
from app.config_validation import config_warnings, validate_settings


def test_validate_settings_warns_on_placeholder_model() -> None:
    status = validate_settings(Settings())

    assert status["status"] == "warning"
    assert any(issue["field"] == "LM_STUDIO_MODEL" for issue in status["issues"])


def test_validate_settings_errors_on_bad_url_and_fetcher() -> None:
    status = validate_settings(
        Settings(
            lm_studio_model="model",
            lm_studio_base_url="not-a-url",
            searxng_base_url="ftp://example.com",
            fetcher="bad",
        )
    )

    assert status["status"] == "error"
    fields = {issue["field"] for issue in status["issues"]}
    assert {"LM_STUDIO_BASE_URL", "SEARXNG_BASE_URL", "FETCHER"} <= fields


def test_config_warnings_renders_issue_messages() -> None:
    warnings = config_warnings(validate_settings(Settings(allow_private_network_fetch=True)))

    assert any("ALLOW_PRIVATE_NETWORK_FETCH" in warning for warning in warnings)
