"""
Messages API — create and retrieve messages within a session.

POST /api/sessions/{session_id}/messages
  - Accepts user message
  - Routes to appropriate agent skill (CHAT/SHIP30/ARTIFACT)
  - Persists both user and assistant messages
  - Returns assistant response with sources

GET /api/sessions/{session_id}/messages
  - Returns all messages in a session
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.artifact import run_artifact
from app.agents.chat import run_chat
from app.agents.router import Intent, route_intent
from app.agents.ship30 import run_ship30
from app.config import get_settings
from app.db.connection import get_db
from app.logging_config import get_logger
from app.models.models import Artifact, Message, Session
from app.providers.base import ProviderConfigError, ProviderTimeoutError, ProviderUnavailableError
from app.providers.factory import get_provider
from app.schemas.schemas import (
    ArtifactResponse,
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    SourceCitation,
)
from app.services.sanitizer import sanitize_for_iframe

logger = get_logger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["messages"])


def _serialize_sources(sources: list[SourceCitation]) -> str | None:
    if not sources:
        return None
    return json.dumps([s.model_dump() for s in sources])


def _deserialize_sources(raw: str | None) -> list[SourceCitation] | None:
    if not raw:
        return None
    try:
        return [SourceCitation(**s) for s in json.loads(raw)]
    except Exception:
        return None


def _msg_to_response(msg: Message) -> MessageResponse:
    return MessageResponse(
        id=msg.id,
        session_id=msg.session_id,
        role=msg.role,
        content=msg.content,
        sources=_deserialize_sources(msg.sources),
        intent=msg.intent,
        created_at=msg.created_at,
    )


@router.get("/{session_id}/messages", response_model=MessageListResponse)
async def get_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MessageListResponse:
    """Retrieve all messages for a session, ordered by creation time."""
    # Verify session exists
    result = await db.execute(select(Session).where(Session.id == session_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    return MessageListResponse(
        messages=[_msg_to_response(m) for m in messages],
        total=len(messages),
    )


@router.post("/{session_id}/messages", response_model=MessageResponse, status_code=201)
async def create_message(
    session_id: uuid.UUID,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Process a user message and return the assistant's response.

    The pipeline:
      1. Validate session exists.
      2. Persist user message.
      3. Load conversation history.
      4. Route intent.
      5. Run appropriate agent skill.
      6. Persist assistant message + sources.
      7. Return assistant message.
    """
    start = time.perf_counter()

    # 1. Validate session
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # 2. Persist user message
    user_msg = Message(
        session_id=session_id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    await db.flush()  # Get ID without committing

    # 3. Load conversation history (exclude the just-added user message)
    history_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .where(Message.id != user_msg.id)
        .order_by(Message.created_at.asc())
    )
    history_messages = history_result.scalars().all()
    conversation_history = [{"role": m.role, "content": m.content} for m in history_messages]

    # 4. Get LLM provider
    try:
        provider = get_provider(body.provider)
    except ProviderConfigError as e:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(e))

    # 5. Route intent
    context_str = " ".join(m["content"][:100] for m in conversation_history[-3:])
    try:
        intent = await route_intent(body.content, provider, context_str)
    except Exception:
        intent = Intent.CHAT

    # 6. Run agent skill
    agent_sources = []
    agent_intent_str = intent.value
    try:
        if intent == Intent.SHIP30:
            result_obj = await run_ship30(body.content, conversation_history, provider, db)
            agent_content = result_obj.content
            agent_sources = result_obj.sources

        elif intent == Intent.ARTIFACT:
            result_obj = await run_artifact(body.content, conversation_history, provider, db)
            agent_content = result_obj.content
            agent_sources = result_obj.sources

            # Save the artifact
            artifact = Artifact(
                session_id=session_id,
                artifact_type=result_obj.artifact_type,
                title=result_obj.title,
                content=result_obj.content,
                sanitized_content=result_obj.sanitized_content,
            )
            db.add(artifact)

        else:  # CHAT
            result_obj = await run_chat(body.content, conversation_history, provider, db)
            agent_content = result_obj.content
            agent_sources = result_obj.sources

    except ProviderUnavailableError as e:
        await db.rollback()
        raise HTTPException(
            status_code=503,
            detail=f"LLM provider unavailable: {str(e)}. Check that Ollama is running or your API key is valid.",
        )
    except ProviderTimeoutError as e:
        await db.rollback()
        raise HTTPException(status_code=504, detail=f"LLM request timed out: {str(e)}")
    except ProviderConfigError as e:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(e))

    # 7. Persist assistant message
    assistant_msg = Message(
        session_id=session_id,
        role="assistant",
        content=agent_content,
        sources=_serialize_sources(agent_sources),
        intent=agent_intent_str,
    )
    db.add(assistant_msg)

    # Update session title from first user message
    if not history_messages:
        # First exchange — auto-title the session
        title = body.content[:80].rstrip("?!.,") + ("..." if len(body.content) > 80 else "")
        session.title = title

    await db.commit()
    await db.refresh(assistant_msg)

    elapsed = time.perf_counter() - start
    logger.info(
        "message.complete",
        session_id=str(session_id),
        intent=agent_intent_str,
        provider=provider.provider_name,
        sources_count=len(agent_sources),
        elapsed_ms=round(elapsed * 1000),
    )

    return _msg_to_response(assistant_msg)
