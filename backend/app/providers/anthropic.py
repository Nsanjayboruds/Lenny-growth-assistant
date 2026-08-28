"""
Anthropic provider — Claude via the official Anthropic Python SDK.
"""
from __future__ import annotations

from typing import Optional

import anthropic

from app.config import get_settings
from app.logging_config import get_logger
from app.providers.base import (
    LLMMessage,
    LLMProvider,
    LLMResponse,
    ProviderConfigError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = get_logger(__name__)

_TIMEOUT_SECONDS = 120


class AnthropicProvider(LLMProvider):
    """
    Calls Anthropic's Messages API using the official SDK.
    Requires ANTHROPIC_API_KEY to be set.
    """

    def __init__(self):
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise ProviderConfigError(
                "ANTHROPIC_API_KEY is not set. "
                "Add your Anthropic API key to .env, or switch LLM_PROVIDER=ollama."
            )
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=_TIMEOUT_SECONDS,
        )
        self._model = settings.anthropic_model

    @property
    def provider_name(self) -> str:
        return "Anthropic Claude (Cloud)"

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
        # Separate system message from conversation
        anthropic_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]
        # Use provided system override or extract from messages
        system_prompt = system or next(
            (m.content for m in messages if m.role == "system"), None
        )

        logger.info("anthropic.generate", model=self._model, message_count=len(anthropic_messages))
        try:
            kwargs: dict = {
                "model": self._model,
                "max_tokens": max_tokens,
                "messages": anthropic_messages,
                "temperature": temperature,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            response = await self._client.messages.create(**kwargs)

        except anthropic.AuthenticationError as e:
            raise ProviderConfigError(f"Invalid Anthropic API key: {e}") from e
        except anthropic.RateLimitError as e:
            raise ProviderUnavailableError(f"Anthropic rate limit exceeded: {e}") from e
        except anthropic.APITimeoutError as e:
            raise ProviderTimeoutError(f"Anthropic request timed out") from e
        except anthropic.APIConnectionError as e:
            raise ProviderUnavailableError(f"Cannot reach Anthropic API: {e}") from e
        except anthropic.APIError as e:
            raise ProviderUnavailableError(f"Anthropic API error: {e}") from e

        content = response.content[0].text if response.content else ""
        return LLMResponse(
            content=content,
            provider="anthropic",
            model=self._model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    async def health_check(self) -> dict:
        try:
            # Make a minimal API call to verify credentials
            test_resp = await self._client.messages.create(
                model=self._model,
                max_tokens=5,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return {
                "status": "ok",
                "detail": f"Anthropic API reachable. Model: {self._model}",
                "model": self._model,
            }
        except ProviderConfigError as e:
            return {"status": "error", "detail": str(e)}
        except Exception as e:
            return {"status": "error", "detail": str(e)}
