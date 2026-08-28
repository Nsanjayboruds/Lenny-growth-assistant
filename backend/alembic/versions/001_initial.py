"""Initial schema: sessions, messages, transcripts, transcript_chunks, artifacts

Revision ID: 001_initial
Revises: 
Create Date: 2026-08-27

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # sessions
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False, server_default="New Chat"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # messages
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("sources", sa.Text, nullable=True),
        sa.Column("intent", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])

    # transcripts
    op.create_table(
        "transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(500), nullable=False, unique=True),
        sa.Column("guest", sa.String(500), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("youtube_url", sa.Text, nullable=True),
        sa.Column("video_id", sa.String(50), nullable=True),
        sa.Column("publish_date", sa.String(50), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("duration", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_transcripts_slug", "transcripts", ["slug"])

    # transcript_chunks with pgvector embedding
    op.create_table(
        "transcript_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transcript_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("guest", sa.String(500), nullable=False),
        sa.Column("episode_title", sa.Text, nullable=False),
        sa.Column("youtube_url", sa.Text, nullable=True),
        sa.UniqueConstraint("transcript_id", "chunk_index", name="uq_chunk_per_transcript"),
    )
    op.create_index("ix_transcript_chunks_transcript_id", "transcript_chunks", ["transcript_id"])
    op.create_index("ix_transcript_chunks_text_hash", "transcript_chunks", ["text_hash"])

    # HNSW vector index for fast approximate nearest neighbor search
    op.execute("""
        CREATE INDEX ix_transcript_chunks_embedding_hnsw
        ON transcript_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # artifacts
    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("sanitized_content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_artifacts_session_id", "artifacts", ["session_id"])


def downgrade() -> None:
    op.drop_table("artifacts")
    op.drop_table("transcript_chunks")
    op.drop_table("transcripts")
    op.drop_table("messages")
    op.drop_table("sessions")
    op.execute("DROP EXTENSION IF EXISTS vector")
