"""
Provider factory — creates the correct LLM provider based on configuration.
"""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.logging_config import get_logger
from app.providers.base import LLMProvider, ProviderConfigError

logger = get_logger(__name__)


def get_provider(override: str | None = None) -> LLMProvider:
    """
    Return an LLMProvider instance based on config or an explicit override.

    Args:
        override: Explicit provider name ("ollama" or "anthropic").
                  Falls back to LLM_PROVIDER env var if None.

    Raises:
        ProviderConfigError: Unknown provider or missing credentials.
    """
    settings = get_settings()
    provider_name = (override or settings.llm_provider).lower()

    logger.info("provider.create", provider=provider_name)

    if provider_name == "ollama":
        from app.providers.ollama import OllamaProvider
        return OllamaProvider()

    elif provider_name == "anthropic":
        from app.providers.anthropic import AnthropicProvider
        return AnthropicProvider()

    else:
        raise ProviderConfigError(
            f"Unknown LLM provider: '{provider_name}'. "
            "Valid options: 'ollama', 'anthropic'."
        )
