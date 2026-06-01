from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx


QUESTIONS = [
    {
        "id": "lmstudio_tool_use",
        "question": "How does LM Studio currently support tool use through its local API?",
        "freshness": "month",
    },
    {
        "id": "searxng_json_api",
        "question": "How do you enable JSON search results in SearXNG?",
        "freshness": "year",
    },
    {
        "id": "free_local_search_stack",
        "question": "What is the best free local-first web search stack to use with LM Studio?",
        "freshness": "month",
    },
]


async def main() -> int:
    results = []
    async with httpx.AsyncClient(timeout=260.0) as client:
        for item in QUESTIONS:
            print(f"RUNNING {item['id']}", flush=True)
            response = await client.post(
                "http://127.0.0.1:8787/ask",
                json={
                    "question": item["question"],
                    "mode": "fast",
                    "freshness": item["freshness"],
                },
            )
            response.raise_for_status()
            data = response.json()
            results.append(
                {
                    "id": item["id"],
                    "question": item["question"],
                    "answer": data["answer"],
                    "model": data.get("model"),
                    "timings_ms": data.get("timings_ms"),
                    "cache_hits": data.get("cache_hits"),
                    "citations": data.get("citations", [])[:8],
                    "warnings": data.get("warnings", []),
                }
            )
            print(
                f"DONE {item['id']} total_ms={data.get('timings_ms', {}).get('total')} "
                f"citations={len(data.get('citations', []))}",
                flush=True,
            )

    out_path = Path("benchmark-results/manual-questions.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

