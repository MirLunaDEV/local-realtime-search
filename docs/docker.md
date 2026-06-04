# Docker

Docker is optional for the MCP-only LM Studio flow, but it is the fastest way to run the local SearXNG backend and the API/UI together.

## Search Backend Only

Use this when LM Studio will call the MCP tool directly:

```powershell
docker compose up -d searxng
```

SearXNG will be available at:

```text
http://127.0.0.1:8080
```

## API/UI Full Stack

Use this when you also want the browser UI and HTTP API:

```powershell
docker compose --profile api up -d
```

The UI will be available at:

```text
http://127.0.0.1:8787
```

Inside Docker, the API container reaches LM Studio through:

```text
http://host.docker.internal:1234/v1
```

Keep LM Studio open with the model you want loaded. Set `LM_STUDIO_MODEL` in `.env` to the exact model ID if you use the API/UI synthesis path:

```powershell
Copy-Item .env.example .env
notepad .env
docker compose --profile api up -d --build
```

The MCP tool path does not require the API container. LM Studio calls `scripts/mcp_server.py` directly through the generated MCP config.

For Docker, `DOCKER_LM_STUDIO_BASE_URL` defaults to `http://host.docker.internal:1234/v1` because `127.0.0.1` inside a container points at the container itself, not your Windows host.

## Windows Helper

Start only SearXNG:

```powershell
.\scripts\start_search_backend.ps1
```

Start SearXNG plus API/UI:

```powershell
.\scripts\start_search_backend.ps1 -Api
```

## Health Checks

SearXNG:

```text
http://127.0.0.1:8080/search?q=health%20check&format=json
```

API/UI:

```text
http://127.0.0.1:8787/health
```

The API health endpoint may report `degraded` when `LM_STUDIO_MODEL` is still the placeholder value. That warning is intentional; it means the container is up, but final answer synthesis needs your loaded model ID.
