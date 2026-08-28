"""
Abstract base class for LLM providers.
All providers must implement this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(ABC):
    """
    Abstract interface for LLM providers.

    Application code depends ONLY on this interface —
    never on OllamaProvider or AnthropicProvider directly.
    """

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            messages: Conversation history (excluding system prompt).
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature (0.0 = deterministic).
            system: Optional system prompt override.

        Returns:
            LLMResponse with generated content and metadata.

        Raises:
            ProviderUnavailableError: Provider cannot be reached.
            ProviderTimeoutError: Request timed out.
            ProviderConfigError: Missing or invalid credentials.
        """
        ...

    @abstractmethod
    async def health_check(self) -> dict:
        """
        Check provider availability and model readiness.

        Returns:
            Dict with at least {"status": "ok" | "error", "detail": str}
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name, e.g. 'Ollama (Local)'"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Current model identifier, e.g. 'llama3.2'"""
        ...


# ── Provider Exceptions ───────────────────────────────────────────────────────

class ProviderError(Exception):
    """Base class for provider errors."""


class ProviderUnavailableError(ProviderError):
    """Provider is unreachable (network error, not running, etc.)"""


class ProviderTimeoutError(ProviderError):
    """Provider timed out responding."""


class ProviderConfigError(ProviderError):
    """Provider is misconfigured (missing API key, invalid model, etc.)"""
