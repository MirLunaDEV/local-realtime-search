from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.pipeline import answer_question
from app.streaming import stream_answer_events


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    mode: str = "fast"
    freshness: str | None = None


app = FastAPI(title="Local Realtime Search", version="0.1.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask")
async def ask(request: AskRequest) -> dict[str, object]:
    settings = get_settings()
    return await answer_question(
        request.question,
        mode=request.mode,
        freshness=request.freshness,
        settings=settings,
    )


@app.get("/ask/stream")
async def ask_stream(question: str, mode: str = "fast", freshness: str | None = None) -> StreamingResponse:
    settings = get_settings()
    return StreamingResponse(
        stream_answer_events(question, mode=mode, freshness=freshness, settings=settings),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
