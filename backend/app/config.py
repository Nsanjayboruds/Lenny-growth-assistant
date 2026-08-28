"""
Central application configuration.
All settings are loaded from environment variables (via .env file in development).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────
    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"

    # ── Database ───────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/lenny"

    # ── LLM Provider ───────────────────────────────────────────────────────
    llm_provider: Literal["ollama", "anthropic"] = "ollama"

    # ── Ollama ─────────────────────────────────────────────────────────────
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"

    # ── Anthropic ──────────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-20241022"

    # ── Retrieval ──────────────────────────────────────────────────────────
    retrieval_top_k: int = 8
    retrieval_score_threshold: float = 0.5

    # ── CORS ───────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
