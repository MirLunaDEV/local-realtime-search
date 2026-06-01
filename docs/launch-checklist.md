# Launch Checklist

## GitHub Profile

- Repository description:
  `Realtime web research MCP for LM Studio local models. No API keys, local SearXNG, clickable sources.`
- Topics:
  `lm-studio`, `mcp`, `searxng`, `local-llm`, `web-search`, `perplexity-alternative`, `openai-compatible`, `qwen`, `rag`, `ai-agents`
- Pin the repository if you want visitors to see it first.

## Demo

Record a short clip showing:

1. LM Studio with a local model loaded.
2. `local_research` being called through MCP.
3. A current question answered with source links.
4. SearXNG running locally in Docker.

Suggested demo question:

```text
Use local_research to answer: What changed recently in LM Studio MCP support? Include sources.
```

## Post Copy

Short:

```text
I built a local realtime web research MCP for LM Studio.

No API keys, no login, local SearXNG, DuckDuckGo fallback, clickable sources, provider health, and direct date/time answers.

It lets your currently loaded LM Studio model call local_research before answering current questions.
```

Long:

```text
I wanted my LM Studio local model to answer current questions with sources without paying for a search API or sending everything to a cloud LLM.

So I built Local Realtime Search: an MCP server for LM Studio that searches local SearXNG, falls back to DuckDuckGo HTML, fetches pages, extracts compact evidence, and returns citation-ready context to the loaded model.

It also has a FastAPI endpoint and browser UI, provider health telemetry, source warnings, SQLite cache, and direct local date/time answers.
```

## Places To Share

- LM Studio Discord
- Reddit `r/LocalLLaMA`
- Reddit `r/LMStudio`
- Reddit `r/mcp`
- Hacker News `Show HN`
- MCP server directories
- Awesome MCP server lists

## Avoid

- Buying stars
- Claiming it is a full Perplexity replacement
- Claiming cloud-level accuracy without caveats
- Hiding that SearXNG is recommended for best results
