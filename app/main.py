from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.config_validation import validate_settings
from app.config import get_settings
from app.observability import log_research_result
from app.pipeline import answer_question
from app.search_backend_health import check_search_backend
from app.streaming import stream_answer_events


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    mode: str = "auto"
    freshness: str | None = None


app = FastAPI(title="Local Realtime Search", version="0.1.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/health")
async def health() -> dict[str, object]:
    settings = get_settings()
    search_backend = await check_search_backend(settings)
    config = validate_settings(settings)
    status = "ok" if search_backend.status == "ok" and config["status"] != "error" else "degraded"
    return {
        "status": status,
        "search_backend": search_backend.to_dict(),
        "config": config,
    }


@app.post("/ask")
async def ask(request: AskRequest) -> dict[str, object]:
    settings = get_settings()
    result = await answer_question(
        request.question,
        mode=request.mode,
        freshness=request.freshness,
        settings=settings,
    )
    log_research_result("ask", result)
    return result


@app.get("/ask/stream")
async def ask_stream(question: str, mode: str = "auto", freshness: str | None = None) -> StreamingResponse:
    settings = get_settings()
    return StreamingResponse(
        stream_answer_events(question, mode=mode, freshness=freshness, settings=settings),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
