from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.search.duckduckgo import DuckDuckGoHtmlProvider


async def main() -> int:
    query = " ".join(sys.argv[1:]) or "LM Studio tool use docs"
    provider = DuckDuckGoHtmlProvider(timeout_seconds=8)
    results = await provider.search(query, limit=5)
    print(f"results={len(results)}")
    for result in results:
        print(f"- {result.title[:90]} | {result.url}")
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
