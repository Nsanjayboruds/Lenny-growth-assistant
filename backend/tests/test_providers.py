"""
Tests for LLM Provider abstractions.
Uses mock HTTP responses to verify the behavior of the provider layer without hitting real APIs.
"""
import pytest
from unittest.mock import AsyncMock, patch

import pytest
from unittest.mock import AsyncMock, patch

from app.providers.base import LLMMessage, ProviderConfigError, ProviderTimeoutError, ProviderUnavailableError
from app.providers.anthropic import AnthropicProvider
from app.providers.ollama import OllamaProvider

@pytest.fixture
def sample_messages():
    return [LLMMessage(role="user", content="Hello")]

@pytest.fixture
def mock_settings():
    with patch("app.providers.ollama.get_settings") as m1, patch("app.providers.anthropic.get_settings") as m2:
        mock_set = AsyncMock()
        mock_set.ollama_base_url = "http://mock"
        mock_set.ollama_model = "llama3.2"
        mock_set.ollama_embedding_model = "nomic"
        mock_set.anthropic_api_key = "fake_key"
        mock_set.anthropic_model = "claude"
        m1.return_value = mock_set
        m2.return_value = mock_set
        yield mock_set

@pytest.mark.asyncio
async def test_ollama_successful_response(sample_messages, mock_settings):
    """Test Ollama returns a valid response on success."""
    provider = OllamaProvider()
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: {"message": {"content": "Hi there"}}

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        res = await provider.generate(sample_messages)
        assert res.content == "Hi there"

@pytest.mark.asyncio
async def test_ollama_unavailable(sample_messages, mock_settings):
    """Test Ollama raises ProviderUnavailableError on connection error."""
    provider = OllamaProvider()
    
    import httpx
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Failed")):
        with pytest.raises(ProviderUnavailableError):
            await provider.generate(sample_messages)

@pytest.mark.asyncio
async def test_ollama_timeout(sample_messages, mock_settings):
    """Test Ollama raises ProviderTimeoutError on timeout."""
    provider = OllamaProvider()
    
    import httpx
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(ProviderTimeoutError):
            await provider.generate(sample_messages)

@pytest.mark.asyncio
async def test_anthropic_successful_response(sample_messages, mock_settings):
    """Test Anthropic returns valid response."""
    provider = AnthropicProvider()
    
    mock_client = AsyncMock()
    mock_msg = AsyncMock()
    mock_msg.content = [AsyncMock(text="Claude says hi")]
    mock_msg.usage = AsyncMock(input_tokens=10, output_tokens=10)
    mock_client.messages.create.return_value = mock_msg
    
    provider._client = mock_client
    
    res = await provider.generate(sample_messages)
    assert res.content == "Claude says hi"

@pytest.mark.asyncio
async def test_missing_anthropic_api_key(mock_settings):
    """Test Anthropic raises ProviderConfigError when key is missing."""
    mock_settings.anthropic_api_key = ""
    with pytest.raises(ProviderConfigError):
        AnthropicProvider()

@pytest.mark.asyncio
async def test_provider_error_normalization(sample_messages, mock_settings):
    """Test Anthropic normalizes API errors into ProviderUnavailableError."""
    provider = AnthropicProvider()
    
    import anthropic
    mock_client = AsyncMock()
    err = anthropic.APIError(message="Server error", request=None, body=None)
    mock_client.messages.create.side_effect = err
    
    provider._client = mock_client
    
    with pytest.raises(ProviderUnavailableError):
        await provider.generate(sample_messages)
