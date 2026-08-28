"""
Artifacts API — create and retrieve generated artifacts.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_db
from app.logging_config import get_logger
from app.models.models import Artifact, Session
from app.schemas.schemas import ArtifactCreate, ArtifactResponse
from app.services.sanitizer import sanitize_for_iframe

logger = get_logger(__name__)
router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.post("", response_model=ArtifactResponse, status_code=201)
async def create_artifact(
    body: ArtifactCreate,
    db: AsyncSession = Depends(get_db),
) -> ArtifactResponse:
    """Manually create an artifact (not via agent pipeline)."""
    # Verify session exists
    result = await db.execute(select(Session).where(Session.id == body.session_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Session {body.session_id} not found")

    sanitized = sanitize_for_iframe(body.content) if body.artifact_type == "html" else body.content

    artifact = Artifact(
        session_id=body.session_id,
        artifact_type=body.artifact_type,
        title=body.title,
        content=body.content,
        sanitized_content=sanitized,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    logger.info("artifact.created", artifact_id=str(artifact.id), artifact_type=artifact.artifact_type)
    return ArtifactResponse.model_validate(artifact)


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ArtifactResponse:
    """Retrieve an artifact by ID."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")
    return ArtifactResponse.model_validate(artifact)


@router.get("/session/{session_id}", response_model=list[ArtifactResponse])
async def get_session_artifacts(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ArtifactResponse]:
    """List all artifacts for a session."""
    result = await db.execute(select(Artifact).where(Artifact.session_id == session_id).order_by(Artifact.created_at.desc()))
    artifacts = result.scalars().all()
    return [ArtifactResponse.model_validate(a) for a in artifacts]
