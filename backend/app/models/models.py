"""
SQLAlchemy ORM models.

Tables:
  sessions       — chat sessions
  messages       — individual chat messages within a session
  transcripts    — Lenny podcast episode metadata
  transcript_chunks — chunked transcript text + pgvector embeddings
  artifacts      — generated Markdown/HTML artifacts
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.connection import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Session(Base):
    """A chat session. Each session is a separate conversation thread."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="New Chat")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="session", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        "Artifact", back_populates="session", cascade="all, delete-orphan"
    )


class Message(Base):
    """A single message in a chat session."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Serialized JSON: list of source citation dicts
    sources: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intent: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # CHAT | SHIP30 | ARTIFACT
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    session: Mapped["Session"] = relationship("Session", back_populates="messages")


class Transcript(Base):
    """Metadata for a Lenny Podcast episode transcript."""

    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Unique identifier: the folder name from the transcript repo (e.g. "brian-chesky")
    slug: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    guest: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    youtube_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    publish_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    chunks: Mapped[list["TranscriptChunk"]] = relationship(
        "TranscriptChunk", back_populates="transcript", cascade="all, delete-orphan"
    )


class TranscriptChunk(Base):
    """
    A semantic chunk of a transcript, with its pgvector embedding.

    The embedding dimension is 768 (nomic-embed-text default).
    If a different embedding model is used, regenerate with a fresh migration.
    """

    __tablename__ = "transcript_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Source hash used for idempotent ingestion (sha256 of text)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # pgvector embedding (768-dim for nomic-embed-text)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(768), nullable=True)
    # Denormalized for fast retrieval display without joining
    guest: Mapped[str] = mapped_column(String(500), nullable=False)
    episode_title: Mapped[str] = mapped_column(Text, nullable=False)
    youtube_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    transcript: Mapped["Transcript"] = relationship("Transcript", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("transcript_id", "chunk_index", name="uq_chunk_per_transcript"),
        Index("ix_transcript_chunks_text_hash", "text_hash"),
        # pgvector HNSW index for fast ANN search — created via migration
    )


class Artifact(Base):
    """A generated artifact (Markdown or HTML) associated with a session."""

    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "markdown" | "html"
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Sanitized version of HTML content (same as content for markdown)
    sanitized_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    session: Mapped["Session"] = relationship("Session", back_populates="artifacts")
