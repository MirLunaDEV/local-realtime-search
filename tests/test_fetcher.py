from app.fetch.fetcher import _looks_low_quality
from app.fetch.http_fetcher import FetchedPage


def test_low_quality_detector_flags_short_text() -> None:
    page = FetchedPage(url="https://example.com", title="Short", text="tiny", status_code=200)

    assert _looks_low_quality(page)


def test_low_quality_detector_accepts_long_clean_text() -> None:
    page = FetchedPage(url="https://example.com", title="Long", text="clean text " * 200, status_code=200)

    assert not _looks_low_quality(page)
