from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.config import get_settings
from app.pipeline import answer_question


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    mode: str = "fast"
    freshness: str | None = None


app = FastAPI(title="Local Realtime Search", version="0.1.0")


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

