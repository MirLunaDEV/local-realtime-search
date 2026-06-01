from app.evidence import EvidenceChunk, select_evidence


def test_select_evidence_filters_weak_sources_when_enough_good_sources() -> None:
    chunks = [
        EvidenceChunk(id=1, title="Instagram", url="https://www.instagram.com/p/example", text="social", provider="test"),
        EvidenceChunk(id=2, title="Blog review", url="https://example.com/blog/review", text="commentary", provider="test"),
        EvidenceChunk(id=3, title="SearXNG API", url="https://docs.searxng.org/dev/search_api.html", text="json api", provider="test"),
        EvidenceChunk(id=4, title="Crawl4AI", url="https://github.com/unclecode/crawl4ai", text="markdown crawler", provider="test"),
        EvidenceChunk(id=5, title="LM Studio", url="https://lmstudio.ai/docs/developer", text="local api", provider="test"),
    ]

    selected = select_evidence(chunks, "LM Studio search stack", limit=5, max_chars=10000)
    urls = {chunk.url for chunk in selected}

    assert "https://www.instagram.com/p/example" not in urls
    assert "https://example.com/blog/review" not in urls
    assert "https://docs.searxng.org/dev/search_api.html" in urls
