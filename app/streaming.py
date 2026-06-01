from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

from app.config import Settings
from app.pipeline import answer_question


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_answer_events(
    question: str,
    *,
    mode: str,
    freshness: str | None,
    settings: Settings,
) -> AsyncIterator[str]:
    started = time.perf_counter()
    yield _sse("status", {"label": "planning", "message": "Planning search strategy"})
    yield _sse("status", {"label": "searching", "message": "Searching configured providers"})
    yield _sse("status", {"label": "fetching", "message": "Fetching and extracting candidate pages"})
    yield _sse("status", {"label": "synthesizing", "message": "Synthesizing grounded answer with LM Studio"})

    result = await answer_question(question, mode=mode, freshness=freshness, settings=settings)

    sources = [
        {
            "title": source.get("title"),
            "url": source.get("url"),
            "source_label": source.get("source_label"),
            "score": source.get("score"),
        }
        for source in list(result.get("sources", []))[:8]
        if isinstance(source, dict)
    ]
    yield _sse("sources", {"sources": sources})
    yield _sse(
        "answer",
        {
            "answer": result.get("answer", ""),
            "citations": result.get("citations", []),
            "timings_ms": result.get("timings_ms", {}),
            "provider_health": result.get("provider_health", []),
            "validation": result.get("validation", {}),
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        },
    )
    yield _sse("done", {"ok": True})
