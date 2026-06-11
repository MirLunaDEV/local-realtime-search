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
- Lightweight answer strategy routing for date, weather, docs, current facts, comparisons, and benchmarks
- Automatic freshness inference for today/latest/weather-style questions
- SQLite search/page cache
- Clickable sources and citation IDs
- Host-diverse result fetching to avoid one site crowding out other sources
- SearXNG backend health diagnostics in `/health`, API responses, and MCP tool results
- SSRF-style URL safety guard for page fetching
- Provider health telemetry and weak-source warnings
- Explicit LM Studio model selection with no hidden fallback
- Safer handling for reasoning models that return empty final content
- `fast`, `balanced`, `deep`, and `deepsearch` research modes

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

To run SearXNG plus the optional browser UI/API in Docker:

```powershell
Copy-Item .env.example .env
# Edit LM_STUDIO_MODEL in .env to match your loaded LM Studio model ID.
docker compose --profile api up -d --build
```

Then open:

```text
http://127.0.0.1:8787
```

Generate an LM Studio MCP config for your machine:

```powershell
uv run python scripts/generate_lmstudio_mcp_config.py
```

On Windows, generate an auto-start config if you want LM Studio to start Docker/SearXNG when the MCP plugin starts:

```powershell
uv run python scripts/generate_lmstudio_mcp_config.py --auto-start-backend
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

To diagnose the local stack from LM Studio, call:

```text
Use local_status to check Docker, SearXNG, API/UI, config, and recent MCP startup logs.
```

To recover the local search backend from LM Studio, call:

```text
Use local_recover to start Docker and SearXNG, then report whether local_research is ready.
```

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

Docker instructions: [`docs/docker.md`](docs/docker.md).

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
| `fast` | Everyday realtime answers | 8 fetches, 8 evidence chunks, 10k evidence chars, 4s+ search timeout, 2400 generation tokens |
| `balanced` | More complete answers | 16 fetches, 20 evidence chunks, 24k evidence chars, 4096 generation tokens |
| `deep` | Slow, broader evidence gathering | 24+ fetches, 40+ evidence chunks, 50k evidence chars, 8192 generation tokens |
| `deepsearch` | Full deep research context for complex questions | 40+ fetches, 72+ evidence chunks, 110k evidence chars, 36 MCP citations, 12k generation tokens |

Every response includes citations, source URLs, timings, cache hits, provider health, warnings, validation metadata, and mode profile.

Responses include `request_id`, and the API/MCP server emits one JSON-line structured log per research request with strategy, latency, citation counts, warning counts, and provider status.

Responses also include `search_backend_status`. If SearXNG is down or returning empty results, the API and MCP tool result add a warning such as:

```text
SearXNG search backend is down at http://127.0.0.1:8080; using fallback sources only.
```

Weather questions use a short `wttr.in` lookup before broad web search. Non-weather questions do not call the weather provider, so this does not add startup latency to normal prompts.

Responses also include `answer_strategy`, a fast rule-based routing hint that tells LM Studio whether the answer should behave like a direct answer, weather lookup, docs lookup, current fact check, comparison, benchmark analysis, or general research.

The MCP server also exposes `local_status`, a diagnostic tool that reports Docker engine reachability, SearXNG health, optional API/UI health, config warnings, recent startup logs, and recommended actions. For one-click recovery, `local_recover` starts Docker/SearXNG through the Windows helper script and then returns fresh health checks.

## Example Prompts

```text
Use local_research to answer: 오늘 날짜와 현재 한국 시간 알려줘.
```

```text
Use local_research to answer: Compare the latest LM Studio MCP support with Open WebUI web search.
```

```text
Use local_research in deepsearch mode to answer: What are the newest Qwen local reasoning model options for LM Studio? Compare sources and cite the main claims.
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
- `ALLOW_PRIVATE_NETWORK_FETCH`: default `false`; blocks page fetches to localhost/private/internal IP ranges
- `RESOLVE_FETCH_HOSTNAMES`: default `true`; resolves hostnames before fetching to catch private-network DNS targets
- `WEATHER_TIMEOUT_SECONDS`: timeout for conditional wttr.in weather lookups
- `LM_STUDIO_MAX_TOKENS`: max generation tokens for answer synthesis
- `SEARCH_TIMEOUT_SECONDS`: default `5.0`; lower values can make free search engines look degraded during slow responses

`/health` also reports config validation warnings/errors, including placeholder model IDs, invalid URLs, invalid fetcher names, unsafe private-network fetch settings, and invalid numeric limits.

Optional Crawl4AI extraction:

```powershell
uv sync --extra crawl4ai
```

Reasoning models may need a large generation budget before they emit final `content`. The default V2 settings use `LM_STUDIO_MAX_TOKENS=4096` and `SYNTHESIS_TIMEOUT_SECONDS=180`.

## Security

The app runs locally, but page fetching still happens from your machine. By default, fetched pages are restricted to `http` and `https` URLs and private/internal targets such as `localhost`, `127.0.0.1`, `192.168.x.x`, `10.x.x.x`, link-local, multicast, and reserved IP ranges are blocked. Hostnames are resolved before fetch so a public-looking domain that points at a private IP is also blocked.

Set `ALLOW_PRIVATE_NETWORK_FETCH=true` only if you intentionally want the assistant to fetch internal sites. Blocked URLs are counted as `blocked_url` and surfaced in warnings instead of being turned into citations.

## Benchmark

With LM Studio, SearXNG, and the FastAPI service running:

```powershell
uv run python scripts/benchmark.py --out benchmark-results/latest.json
```

For a quick smoke run:

```powershell
uv run python scripts/benchmark.py --category direct_answer --category weather --out benchmark-results/smoke.json
```

To inspect or run specific cases:

```powershell
uv run python scripts/benchmark.py --list-cases
uv run python scripts/benchmark.py --case-id lmstudio_mcp --out benchmark-results/lmstudio-mcp.json
```

The benchmark records latency, citation count, expected-domain hits, warnings, and answer previews across mixed question types.

Each case in [`benchmarks/questions.json`](benchmarks/questions.json) can also define quality gates such as `min_citations`, `expected_domains`, `expected_answer_strategy`, `allowed_search_backend_statuses`, `required_evidence_terms`, `required_any_evidence_terms`, and `forbidden_answer_terms`. Failed gates are reported per case in `failure_reasons`, so regressions are easier to diagnose than a single pass/fail number.

Compare against a previous baseline:

```powershell
uv run python scripts/benchmark.py `
  --baseline benchmark-results/baseline.json `
  --out benchmark-results/latest.json `
  --compare-out benchmark-results/comparison.json `
  --fail-on-regression `
  --max-p90-regression-ms 5000 `
  --min-success-rate 1.0 `
  --min-expected-domain-rate 0.8
```

Use `--mode deepsearch` for the heavier research suite when you want to stress large-context local models.

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

`deepsearch` expands query variants, candidate URLs, fetched pages, per-page evidence chunks, total evidence characters, and MCP citation payload size. It is slower than `deep`, but it gives larger-context local models much more research material before they write the final answer.

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

To start Docker/SearXNG automatically when LM Studio starts the MCP plugin, use the generated wrapper config:

```powershell
uv run python scripts/generate_lmstudio_mcp_config.py --auto-start-backend
```

The wrapper writes startup diagnostics to `.cache/mcp-startup.log` and MCP research event logs to `.cache/mcp-events.jsonl`.

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
- Docker guide: [`docs/docker.md`](docs/docker.md)
- MCP config template: [`mcp/lmstudio.mcp.json`](mcp/lmstudio.mcp.json)

## License

MIT
