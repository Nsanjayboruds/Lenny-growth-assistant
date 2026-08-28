"""
Sessions API — CRUD operations for chat sessions.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_db
from app.logging_config import get_logger
from app.models.models import Message, Session
from app.schemas.schemas import (
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Create a new chat session."""
    session = Session(title=body.title, user_id=body.user_id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info("session.created", session_id=str(session.id), user_id=body.user_id)
    return SessionResponse(
        id=session.id,
        title=session.title,
        user_id=session.user_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    """List all sessions, ordered by most recently updated."""
    result = await db.execute(
        select(Session).order_by(Session.updated_at.desc())
    )
    sessions = result.scalars().all()

    session_responses = []
    for s in sessions:
        count_result = await db.execute(
            select(func.count(Message.id)).where(Message.session_id == s.id)
        )
        count = count_result.scalar() or 0
        session_responses.append(
            SessionResponse(
                id=s.id,
                title=s.title,
                user_id=s.user_id,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=count,
            )
        )

    return SessionListResponse(sessions=session_responses, total=len(session_responses))


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Get a single session by ID."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    count_result = await db.execute(
        select(func.count(Message.id)).where(Message.session_id == session_id)
    )
    count = count_result.scalar() or 0

    return SessionResponse(
        id=session.id,
        title=session.title,
        user_id=session.user_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=count,
    )


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: uuid.UUID,
    body: SessionUpdate,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Update session title."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    session.title = body.title
    await db.commit()
    await db.refresh(session)

    count_result = await db.execute(
        select(func.count(Message.id)).where(Message.session_id == session_id)
    )
    count = count_result.scalar() or 0

    return SessionResponse(
        id=session.id,
        title=session.title,
        user_id=session.user_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=count,
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a session and all its messages (cascade)."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    await db.delete(session)
    await db.commit()
    logger.info("session.deleted", session_id=str(session_id))
    return Response(status_code=204)
