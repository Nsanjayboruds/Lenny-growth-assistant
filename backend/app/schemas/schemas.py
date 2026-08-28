"""
Pydantic schemas for API request/response validation.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Source Citation ─────────────────────────────────────────────────────────

class SourceCitation(BaseModel):
    episode_title: str
    guest: str
    youtube_url: Optional[str] = None
    chunk_text: str
    score: float


# ── Sessions ─────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=500)
    user_id: Optional[str] = Field(default=None, max_length=255, description="Anonymous or authenticated user identifier")


class SessionUpdate(BaseModel):
    title: str = Field(..., max_length=500)


class SessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int


# ── Messages ─────────────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    provider: Optional[str] = Field(default=None, description="Override LLM provider: 'ollama' or 'anthropic'")


class MessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    sources: Optional[list[SourceCitation]] = None
    intent: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    total: int


# ── Artifacts ─────────────────────────────────────────────────────────────────

class ArtifactCreate(BaseModel):
    session_id: uuid.UUID
    artifact_type: str = Field(..., pattern="^(markdown|html)$")
    title: str = Field(..., max_length=500)
    content: str = Field(..., min_length=1)


class ArtifactResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    artifact_type: str
    title: str
    content: str
    sanitized_content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Health ────────────────────────────────────────────────────────────────────

class HealthStatus(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    checks: dict[str, Any]
    version: str = "1.0.0"


# ── Error ─────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
