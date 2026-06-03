# LM Studio Realtime Search MCP

[![CI](https://github.com/MirLunaDEV/local-realtime-search/actions/workflows/ci.yml/badge.svg)](https://github.com/MirLunaDEV/local-realtime-search/actions/workflows/ci.yml)

Give LM Studio local models ChatGPT-like realtime web research through MCP.

No API keys. No login. Local SearXNG. Clickable sources. Works with the model you already loaded in LM Studio.

```text
LM Studio chat model
-> MCP local_research tool
-> SearXNG + DuckDuckGo fallback + page extraction
-> citations, source links, provider health, warnings
-> your local model writes the final answer
```

## Why This Exists

Local models are good, but they usually miss current information. This project adds a local realtime research layer for LM Studio without routing your questions through paid search APIs or cloud LLMs.

Use it for:

- current news, release notes, docs, prices, dates, weather, and changing facts
- source-backed benchmark or product comparisons
- Korean and English web research
- local-only LM Studio workflows with MCP tools

## Features

- `local_research` MCP tool for LM Studio
- FastAPI endpoint and local browser UI
- SearXNG Docker search backend, optional but recommended
- DuckDuckGo HTML fallback when SearXNG is unavailable
- Direct local date/time answers without model/search calls
- Conditional wttr.in weather provider for weather questions
- Automatic freshness inference for today/latest/weather-style questions
- SQLite search/page cache
- Clickable sources and citation IDs
- Host-diverse result fetching to avoid one site crowding out other sources
- SearXNG backend health diagnostics in `/health`, API responses, and MCP tool results
- Provider health telemetry and weak-source warnings
- Explicit LM Studio model selection with no hidden fallback
- Safer handling for reasoning models that return empty final content
- `fast`, `balanced`, and `deep` research modes

## Quick Start

Requirements:

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop, for local SearXNG
- LM Studio 0.3.17+ with MCP support

Clone and install:

```powershell
git clone https://github.com/MirLunaDEV/local-realtime-search.git
cd local-realtime-search
uv sync --extra mcp
```

Start local search:

```powershell
docker compose up -d searxng
```

On Windows, you can also start Docker Desktop and SearXNG together:

```powershell
.\scripts\start_search_backend.ps1
```

Generate an LM Studio MCP config for your machine:

```powershell
uv run python scripts/generate_lmstudio_mcp_config.py
```

Copy the printed JSON into LM Studio:

```text
Program tab -> Install -> Edit mcp.json
```

Then ask in LM Studio:

```text
Use local_research to answer: What changed recently in LM Studio MCP support?
```

If the tool call appears and returns citations/source URLs, it is working.

## MCP Config

An example config lives at [`mcp/lmstudio.mcp.json`](mcp/lmstudio.mcp.json).

For Windows, the generated config is safer than hand-editing because it uses the exact `uv.exe` path on your machine.

```powershell
uv run python scripts/generate_lmstudio_mcp_config.py --model "your-loaded-lm-studio-model-id"
```

The MCP tool intentionally does not call LM Studio for final synthesis. LM Studio calls `local_research`, receives compact evidence, then the currently loaded chat model writes the final answer.

## Optional Web UI

The project also includes a local research UI:

```powershell
uvicorn app.main:app --reload --port 8787
```

Open:

```text
http://127.0.0.1:8787
```

The UI streams progress states, answer text, source links, provider health, warnings, and timings.

Check backend health:

```text
http://127.0.0.1:8787/health
```

The health response includes `search_backend.status` so you can tell whether SearXNG is `ok`, `empty`, or `down`.

## API Usage

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8787/ask `
  -ContentType application/json `
  -Body '{"question":"What changed recently in LM Studio tool use?","mode":"fast","freshness":"month"}'
```

Available modes:

| Mode | Use case | Default profile |
|---|---|---|
| `fast` | Everyday realtime answers | 8 fetches, 8 evidence chunks, 10k evidence chars, 2400 generation tokens |
| `balanced` | More complete answers | 16 fetches, 20 evidence chunks, 24k evidence chars, 4096 generation tokens |
| `deep` | Slow, broader evidence gathering | 24+ fetches, 40+ evidence chunks, 50k evidence chars, 8192 generation tokens |

Every response includes citations, source URLs, timings, cache hits, provider health, warnings, validation metadata, and mode profile.

Responses also include `search_backend_status`. If SearXNG is down or returning empty results, the API and MCP tool result add a warning such as:

```text
SearXNG search backend is down at http://127.0.0.1:8080; using fallback sources only.
```

Weather questions use a short `wttr.in` lookup before broad web search. Non-weather questions do not call the weather provider, so this does not add startup latency to normal prompts.

## Example Prompts

```text
Use local_research to answer: 오늘 날짜와 현재 한국 시간 알려줘.
```

```text
Use local_research to answer: Compare the latest LM Studio MCP support with Open WebUI web search.
```

```text
Use local_research in deep mode to answer: What are the newest Qwen local reasoning model options for LM Studio?
```

More examples: [`examples/prompts.md`](examples/prompts.md).

## Configuration

Copy `.env.example` to `.env` or set environment variables directly.

Important variables:

- `LM_STUDIO_BASE_URL`: default `http://127.0.0.1:1234/v1`
- `LM_STUDIO_MODEL`: exact model ID loaded in LM Studio
- `LOCAL_TIMEZONE`: timezone for direct date/time answers
- `SEARXNG_BASE_URL`: default `http://127.0.0.1:8080`
- `CACHE_PATH`: SQLite cache path
- `FETCHER`: `auto`, `http`, or `crawl4ai`
- `WEATHER_TIMEOUT_SECONDS`: timeout for conditional wttr.in weather lookups
- `LM_STUDIO_MAX_TOKENS`: max generation tokens for answer synthesis

Optional Crawl4AI extraction:

```powershell
uv sync --extra crawl4ai
```

Reasoning models may need a large generation budget before they emit final `content`. The default V2 settings use `LM_STUDIO_MAX_TOKENS=4096` and `SYNTHESIS_TIMEOUT_SECONDS=180`.

## Benchmark

With LM Studio, SearXNG, and the FastAPI service running:

```powershell
uv run python scripts/benchmark.py --out benchmark-results/latest.json
```

The benchmark records latency, citation count, expected-domain hits, warnings, and answer previews across mixed question types.

## How It Compares

| Project type | This project |
|---|---|
| Full Perplexity clone | No. This is a focused LM Studio research tool. |
| General LLM web UI | No. It plugs into LM Studio through MCP. |
| Cloud search API wrapper | No. It works with local SearXNG and free fallbacks. |
| Simple search MCP | More than that. It fetches pages, ranks evidence, reports health, and returns citation-ready context. |

## Architecture

1. Plan search query variants.
2. Query official hints, SearXNG, and DuckDuckGo fallback in parallel.
3. Deduplicate and rank candidate URLs.
4. Select a host-diverse fetch set with strict timeouts.
5. Extract compact evidence chunks.
6. Return citation-ready context to LM Studio or synthesize through the API/UI path.

## Troubleshooting

Docker is not running:

```text
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified
```

Start Docker Desktop, then run:

```powershell
docker compose up -d searxng
```

Or use the helper script:

```powershell
.\scripts\start_search_backend.ps1
```

MCP cannot import `app`:

```text
ModuleNotFoundError: No module named 'app'
```

Update to the latest commit. The MCP server now injects the project root into `sys.path`.

LM Studio shows no tool:

- verify the JSON was saved in LM Studio's `mcp.json`
- use the generated config script so `uv.exe` and `cwd` are correct
- restart LM Studio after editing MCP config

## Launch Links

- Demo prompts: [`examples/prompts.md`](examples/prompts.md)
- Launch checklist: [`docs/launch-checklist.md`](docs/launch-checklist.md)
- MCP config template: [`mcp/lmstudio.mcp.json`](mcp/lmstudio.mcp.json)

## License

MIT
