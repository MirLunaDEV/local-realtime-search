from __future__ import annotations

from typing import Any

import pytest

from app.search.source_discovery import GitHubRepositoryProvider, HuggingFaceModelsProvider


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._payload


class FakeAsyncClient:
    calls: list[tuple[str, dict[str, Any] | None]] = []
    payload: Any = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> FakeAsyncClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def get(self, url: str, *, params: dict[str, Any] | None = None) -> FakeResponse:
        self.calls.append((url, params))
        return FakeResponse(self.payload)


@pytest.mark.anyio
async def test_huggingface_provider_reuses_subject_cache(monkeypatch) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.payload = [
        {
            "modelId": "google/gemma-4-12b-it",
            "downloads": 10,
            "likes": 2,
            "pipeline_tag": "text-generation",
            "lastModified": "2026-06-01T00:00:00Z",
        }
    ]
    monkeypatch.setattr("app.search.source_discovery.httpx.AsyncClient", FakeAsyncClient)
    provider = HuggingFaceModelsProvider(timeout_seconds=1.0)

    first = await provider.search("Gemma 4 12B benchmark", limit=10)
    second = await provider.search("Gemma 4 12B Reddit review", limit=10)

    assert len(FakeAsyncClient.calls) == 1
    assert first == second
    assert first[0].url == "https://huggingface.co/google/gemma-4-12b-it"


@pytest.mark.anyio
async def test_github_provider_reuses_subject_cache(monkeypatch) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.payload = {
        "items": [
            {
                "html_url": "https://github.com/example/gemma-eval",
                "full_name": "example/gemma-eval",
                "description": "Gemma evaluation scripts",
                "stargazers_count": 4,
                "updated_at": "2026-06-01T00:00:00Z",
            }
        ]
    }
    monkeypatch.setattr("app.search.source_discovery.httpx.AsyncClient", FakeAsyncClient)
    provider = GitHubRepositoryProvider(timeout_seconds=1.0)

    first = await provider.search("Gemma 4 12B benchmark", limit=10)
    second = await provider.search("Gemma 4 12B GitHub issues", limit=10)

    assert len(FakeAsyncClient.calls) == 1
    assert first == second
    assert first[0].url == "https://github.com/example/gemma-eval"
