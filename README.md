# Local Realtime Search

[![CI](https://github.com/MirLunaDEV/local-realtime-search/actions/workflows/ci.yml/badge.svg)](https://github.com/MirLunaDEV/local-realtime-search/actions/workflows/ci.yml)

Fast realtime web evidence layer for LM Studio local models.

This prototype is intentionally optimized for normal assistant-style answers, not long-running deep research. It searches broadly, fetches shallowly, compresses evidence, and asks the local model to answer with citations.

## Requirements

- Python 3.11+
- LM Studio with the local server enabled
- A running SearXNG instance, optional but recommended

## Install

```powershell
uv sync
```

or:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -e .
```

## Configure

Copy `.env.example` to `.env` or set environment variables directly.

Important variables:

- `LM_STUDIO_BASE_URL`: default `http://127.0.0.1:1234/v1`
- `LM_STUDIO_MODEL`: model name loaded in LM Studio
- `SEARXNG_BASE_URL`: your SearXNG base URL
- `CACHE_PATH`: SQLite cache path
- `FETCHER`: `auto`, `http`, or `crawl4ai`
- `LM_STUDIO_MAX_TOKENS`: max generation tokens for answer synthesis

If SearXNG is not running, the prototype also tries a free DuckDuckGo HTML fallback. This is useful for local testing, but SearXNG is still the better self-hosted default.

`FETCHER=auto` uses the fast HTTP extractor first, then tries Crawl4AI only when the fetched page looks too thin or broken. Crawl4AI is optional:

```powershell
uv sync --extra crawl4ai
```

The app does not auto-switch models. Set `LM_STUDIO_MODEL` to the exact model ID loaded in LM Studio. If that model is unavailable or returns no final content, synthesis fails visibly instead of silently falling back to another model.

Reasoning models may need a large generation budget before they emit final `content`. The default V2 settings use `LM_STUDIO_MAX_TOKENS=4096` and `SYNTHESIS_TIMEOUT_SECONDS=180` for this reason.

## Run

Start the local SearXNG search backend:

```powershell
docker compose up -d searxng
```

Then start the API:

```powershell
uvicorn app.main:app --reload --port 8787
```

## Ask

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8787/ask `
  -ContentType application/json `
  -Body '{"question":"What changed recently in LM Studio tool use?","mode":"fast","freshness":"month"}'
```

Available modes:

| Mode | Use case | Default profile |
|---|---|---|
| `fast` | Everyday realtime answers | 8 fetches, 8 evidence chunks, 10k evidence chars, 2400 generation tokens, 90s synthesis timeout |
| `balanced` | More complete answers | 16 fetches, 20 evidence chunks, 24k evidence chars, 4096 generation tokens, 180s synthesis timeout |
| `deep` | Slow, broader evidence gathering | 24+ fetches, 40+ evidence chunks, 50k evidence chars, 8192 generation tokens, 420s synthesis timeout |

Every response includes `mode_profile`, `validation`, `knowledge_prior`, timings, citations, sources, warnings, cache hit metadata, `fetcher_counts`, `search_traces`, and `provider_health`.

## Benchmark

With LM Studio, SearXNG, and the FastAPI service running:

```powershell
uv run python scripts/benchmark.py --out benchmark-results/latest.json
```

The benchmark records latency, citation count, expected-domain hits, warnings, and answer previews across mixed question types.

The default question set has 15 mixed questions covering LM Studio, SearXNG, Crawl4AI, Korean queries, local architecture, citation quality, cache strategy, and context/max-token tuning.

## Design

Pipeline:

1. Plan 3-6 search query variants.
2. Query SearXNG in parallel.
3. Deduplicate and rank candidate URLs.
4. Fetch top pages with strict timeouts.
5. Extract compact evidence chunks.
6. Ask LM Studio for a cited answer.

Every response includes timings, sources, citations, and warnings when evidence is weak.

## V2 Notes

V2 adds:

- Explicit LM Studio model selection with no automatic fallback.
- Source policy scoring for official docs, GitHub, government sites, docs, release notes, social/video, and commentary.
- SQLite search/page cache.
- `cache_hits` response metadata.
- Provider health telemetry for search providers.
- Safer failure when reasoning models return empty final content.
- `fast`, `balanced`, and `deep` mode profiles.
- Knowledge priors for stable architecture guidance.
- Answer validation for citation IDs, weak sources, and prior drift.
- Optional Crawl4AI extraction fallback through `FETCHER=auto` or `FETCHER=crawl4ai`.
- Expanded 15-question benchmark set.
- Korean local-stack query handling for LM Studio + SearXNG + Crawl4AI recommendations.
- Architecture-question grounding for cache strategy and citation-quality answers.
- Prior-specific answer cleanup for default local cache recommendations.
