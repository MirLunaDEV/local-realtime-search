from app.config import Settings
from app.search_backend_health import status_from_provider_health


def test_status_from_provider_health_reports_down_backend() -> None:
    status = status_from_provider_health(
        [
            {
                "provider": "searxng",
                "status": "down",
                "requests": 2,
                "result_count": 0,
                "avg_elapsed_ms": 1200,
            }
        ],
        Settings(searxng_base_url="http://127.0.0.1:8080"),
    )

    assert status.status == "down"
    assert "did not respond" in str(status.error)


def test_status_from_provider_health_reports_not_used() -> None:
    status = status_from_provider_health([], Settings())

    assert status.status == "not_used"
