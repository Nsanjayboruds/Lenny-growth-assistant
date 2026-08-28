"""
Health check endpoint.

Reports status of:
  - API (always available if this responds)
  - PostgreSQL
  - Ollama (current LLM provider)
  - pgvector extension
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.connection import get_db
from app.logging_config import get_logger
from app.providers.factory import get_provider
from app.schemas.schemas import HealthStatus

logger = get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthStatus:
    """
    Comprehensive health check.
    Returns 200 even if some dependencies are degraded (never crashes the API).
    """
    settings = get_settings()
    checks: dict = {}

    # ── PostgreSQL ──────────────────────────────────────────────────────────
    try:
        result = await db.execute(text("SELECT 1"))
        checks["postgres"] = {"status": "ok"}
    except Exception as e:
        checks["postgres"] = {"status": "error", "detail": str(e)}

    # ── pgvector extension ──────────────────────────────────────────────────
    try:
        result = await db.execute(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
        pgvector_installed = result.scalar()
        checks["pgvector"] = {
            "status": "ok" if pgvector_installed else "error",
            "detail": "Extension installed" if pgvector_installed else "Extension NOT installed — run: CREATE EXTENSION vector;",
        }
    except Exception as e:
        checks["pgvector"] = {"status": "error", "detail": str(e)}

    # ── LLM Provider ────────────────────────────────────────────────────────
    try:
        provider = get_provider()
        provider_health = await provider.health_check()
        checks["llm_provider"] = {
            "provider": provider.provider_name,
            "model": provider.model_name,
            **provider_health,
        }
    except Exception as e:
        checks["llm_provider"] = {"status": "error", "detail": str(e)}

    # ── Transcript chunks count ─────────────────────────────────────────────
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM transcript_chunks"))
        chunk_count = result.scalar()
        result2 = await db.execute(
            text("SELECT COUNT(*) FROM transcript_chunks WHERE embedding IS NOT NULL")
        )
        embedded_count = result2.scalar()
        checks["knowledge_base"] = {
            "status": "ok" if embedded_count and embedded_count > 0 else "degraded",
            "total_chunks": chunk_count,
            "embedded_chunks": embedded_count,
            "detail": "Ready for RAG" if embedded_count and embedded_count > 0 else "Run ingestion pipeline first",
        }
    except Exception as e:
        checks["knowledge_base"] = {"status": "error", "detail": str(e)}

    # Determine overall status
    statuses = [v.get("status", "error") for v in checks.values() if isinstance(v, dict)]
    if all(s == "ok" for s in statuses):
        overall = "healthy"
    elif any(s == "error" for s in statuses):
        overall = "degraded"
    else:
        overall = "degraded"

    logger.info("health.check", overall=overall, checks=checks)
    return HealthStatus(status=overall, checks=checks)
