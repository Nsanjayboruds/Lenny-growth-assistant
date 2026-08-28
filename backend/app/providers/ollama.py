"""
Ollama provider — local inference via Ollama HTTP API.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from app.config import get_settings
from app.logging_config import get_logger
from app.providers.base import (
    LLMMessage,
    LLMProvider,
    LLMResponse,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = get_logger(__name__)

_TIMEOUT_SECONDS = 600
_CONNECT_TIMEOUT = 10


class OllamaProvider(LLMProvider):
    """
    Calls Ollama's /api/chat endpoint for text generation.
    Uses Ollama's /api/embeddings endpoint for vector embeddings.

    Model must already be pulled: `ollama pull <model>`.
    """

    def __init__(self):
        settings = get_settings()
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._embedding_model = settings.ollama_embedding_model

    @property
    def provider_name(self) -> str:
        return "Ollama (Local)"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system: Optional[str] = None,
    ) -> LLMResponse:
        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        formatted_messages.extend([{"role": m.role, "content": m.content} for m in messages])

        payload: dict = {
            "model": self._model,
            "messages": formatted_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        logger.info("ollama.generate", model=self._model, message_count=len(messages))
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(_TIMEOUT_SECONDS, connect=_CONNECT_TIMEOUT)) as client:
                resp = await client.post(f"{self._base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()

        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(f"Ollama request timed out after {_TIMEOUT_SECONDS}s") from e
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(
                f"Cannot reach Ollama at {self._base_url}. "
                "Is Ollama running? Try: ollama serve"
            ) from e
        except httpx.HTTPStatusError as e:
            raise ProviderUnavailableError(f"Ollama returned HTTP {e.response.status_code}: {e.response.text}") from e

        content = data.get("message", {}).get("content", "")
        eval_count = data.get("eval_count", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)

        return LLMResponse(
            content=content,
            provider="ollama",
            model=self._model,
            input_tokens=prompt_eval_count,
            output_tokens=eval_count,
        )

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=_CONNECT_TIMEOUT)) as client:
                resp = await client.post(
                    f"{self._base_url}/api/embed",
                    json={"model": self._embedding_model, "input": text},
                )
                resp.raise_for_status()
                data = resp.json()
                # Ollama /api/embed returns {"embeddings": [[...]]}
                embeddings = data.get("embeddings", [])
                if embeddings:
                    return embeddings[0]
                raise ProviderUnavailableError("Ollama returned empty embeddings")
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(f"Cannot reach Ollama at {self._base_url}") from e
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError("Ollama embedding request timed out") from e

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5, connect=3)) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                chat_model_available = any(self._model in m for m in models)
                embed_model_available = any(self._embedding_model in m for m in models)
                return {
                    "status": "ok" if chat_model_available else "degraded",
                    "detail": f"Ollama running. Chat model '{self._model}' available: {chat_model_available}. "
                              f"Embed model '{self._embedding_model}' available: {embed_model_available}.",
                    "available_models": models,
                    "chat_model_ready": chat_model_available,
                    "embed_model_ready": embed_model_available,
                }
        except Exception as e:
            return {"status": "error", "detail": str(e)}
