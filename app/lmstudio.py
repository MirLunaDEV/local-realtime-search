from __future__ import annotations

import httpx


class EmptyFinalContentError(RuntimeError):
    def __init__(self, *, finish_reason: str | None, reasoning_preview: str = "") -> None:
        self.finish_reason = finish_reason
        self.reasoning_preview = reasoning_preview
        super().__init__(
            "LM Studio returned empty final content for the configured model. "
            f"finish_reason={finish_reason}. "
            "The model produced reasoning_content but no user-facing content."
        )


class LmStudioClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
        max_tokens: int = 1200,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens

    async def _assert_model_available(self, client: httpx.AsyncClient) -> None:
        response = await client.get(f"{self.base_url}/models")
        response.raise_for_status()
        model_ids = [str(item.get("id")) for item in response.json().get("data", []) if item.get("id")]
        if self.model not in model_ids:
            available = ", ".join(model_ids[:12])
            raise RuntimeError(
                f"Configured LM Studio model '{self.model}' is not available. "
                f"Load that model in LM Studio or set LM_STUDIO_MODEL. Available: {available}"
            )

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        headers = {"authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers) as client:
            await self._assert_model_available(client)
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens or self.max_tokens,
            }
            try:
                response = await client.post(f"{self.base_url}/chat/completions", json=payload)
            except httpx.ReadTimeout as exc:
                raise RuntimeError(
                    "LM Studio request timed out before returning final content. "
                    "For reasoning models, this usually means the model stayed in reasoning mode "
                    "and did not reach the answer channel within the timeout."
                ) from exc
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = response.text[:1000]
                raise RuntimeError(f"LM Studio request failed: {response.status_code} {detail}") from exc
            data = response.json()
        message = data["choices"][0]["message"]
        content = str(message.get("content") or "").strip()
        if not content:
            finish_reason = data["choices"][0].get("finish_reason")
            reasoning_preview = str(message.get("reasoning_content") or "")[:500]
            raise EmptyFinalContentError(
                finish_reason=str(finish_reason) if finish_reason else None,
                reasoning_preview=reasoning_preview,
            )
        return content
