"""
ingestion/index.py — Main ingestion orchestrator.

Run with:
  python ingestion/index.py

This script:
  1. Clones/updates the transcript repository.
  2. Parses all transcripts.
  3. Chunks each transcript body.
  4. Embeds each chunk via Ollama.
  5. Stores transcripts + chunks in PostgreSQL/pgvector.
  6. Is idempotent: skips transcripts/chunks that already exist.

Environment variables (or .env):
  DATABASE_URL  — PostgreSQL connection string
  OLLAMA_BASE_URL — Ollama instance URL
  OLLAMA_EMBEDDING_MODEL — embedding model name
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import time
import uuid
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import asyncpg
from dotenv import load_dotenv
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv(Path(__file__).parent.parent / ".env")

from app.models.models import Transcript, TranscriptChunk

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/lenny")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

from ingestion.download import download_transcripts
from ingestion.parse import load_all_transcripts
from ingestion.chunk import chunk_transcript
from ingestion.embed import embed_batch


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def ingest(force_download: bool = False) -> None:
    print("=" * 60)
    print("Lenny Growth Assistant — Ingestion Pipeline")
    print("=" * 60)

    # Step 1: Download
    print("\n[1/5] Downloading transcripts...")
    repo_dir = download_transcripts(force_update=force_download)

    # Step 2: Parse
    print("\n[2/5] Parsing transcripts...")
    transcripts = load_all_transcripts(repo_dir)
    if not transcripts:
        print("No transcripts found. Exiting.")
        return
    print(f"      Found {len(transcripts)} transcripts.")

    # Step 3: Connect to DB
    print("\n[3/5] Connecting to database...")
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Step 4: Index transcripts + chunks
    print("\n[4/5] Indexing transcripts and chunks (idempotent)...")
    total_transcripts = 0
    total_chunks_new = 0
    total_chunks_skipped = 0

    async with session_factory() as db:
        for t in transcripts:
            # Check if transcript already exists
            result = await db.execute(select(Transcript).where(Transcript.slug == t.slug))
            existing_transcript = result.scalar_one_or_none()

            if existing_transcript:
                transcript_id = existing_transcript.id
            else:
                new_transcript = Transcript(
                    slug=t.slug,
                    guest=t.guest,
                    title=t.title,
                    youtube_url=t.youtube_url,
                    video_id=t.video_id,
                    publish_date=t.publish_date,
                    description=t.description,
                    duration=t.duration,
                )
                db.add(new_transcript)
                await db.flush()
                transcript_id = new_transcript.id
                total_transcripts += 1

            # Chunk the transcript
            chunks = chunk_transcript(t.body)
            if not chunks:
                continue

            # Find existing chunk hashes for this transcript
            result = await db.execute(
                select(TranscriptChunk.text_hash)
                .where(TranscriptChunk.transcript_id == transcript_id)
            )
            existing_hashes = set(row[0] for row in result.fetchall())

            # Filter to only new chunks
            new_chunks = []
            for c in chunks:
                chunk_hash = _sha256(c.text)
                if chunk_hash not in existing_hashes:
                    new_chunks.append((c, chunk_hash))
                else:
                    total_chunks_skipped += 1

            if not new_chunks:
                continue

            # Embed new chunks
            texts_to_embed = [c.text for c, _ in new_chunks]

            print(f"  Embedding {len(texts_to_embed)} new chunks for: {t.slug[:40]}...")
            embeddings = await embed_batch(
                texts_to_embed,
                base_url=OLLAMA_BASE_URL,
                model=OLLAMA_EMBEDDING_MODEL,
                show_progress=False,
            )

            # Persist new chunks
            for (c, chunk_hash), embedding in zip(new_chunks, embeddings):
                chunk = TranscriptChunk(
                    transcript_id=transcript_id,
                    chunk_index=c.chunk_index,
                    text=c.text,
                    text_hash=chunk_hash,
                    embedding=embedding,
                    guest=t.guest,
                    episode_title=t.title,
                    youtube_url=t.youtube_url,
                )
                db.add(chunk)
                total_chunks_new += 1

            await db.commit()

    await engine.dispose()

    print(f"\n[5/5] Ingestion complete!")
    print(f"      New transcripts: {total_transcripts}")
    print(f"      New chunks embedded: {total_chunks_new}")
    print(f"      Chunks skipped (already indexed): {total_chunks_skipped}")
    print()


if __name__ == "__main__":
    force = "--force" in sys.argv
    start = time.perf_counter()
    asyncio.run(ingest(force_download=force))
    elapsed = time.perf_counter() - start
    print(f"Total time: {elapsed:.1f}s")
