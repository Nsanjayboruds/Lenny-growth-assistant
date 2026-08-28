"""
ingestion/chunk.py — Paragraph-aware transcript chunker.

Strategy:
  - Split on double newlines (paragraph boundaries).
  - Respect speaker turn boundaries (lines like "Lenny:", "Guest:").
  - Merge small paragraphs into chunks of ~600 tokens with 100-token overlap.
  - Never split a speaker turn mid-sentence.

This produces semantically coherent chunks better suited for RAG than
fixed-character splitting.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Approximate tokens per character for English text
_CHARS_PER_TOKEN = 4
_TARGET_CHUNK_TOKENS = 600
_TARGET_CHUNK_CHARS = _TARGET_CHUNK_TOKENS * _CHARS_PER_TOKEN   # ~2400 chars
_OVERLAP_TOKENS = 100
_OVERLAP_CHARS = _OVERLAP_TOKENS * _CHARS_PER_TOKEN              # ~400 chars
_MIN_CHUNK_CHARS = 200  # Skip very short chunks (headers, timestamps)


@dataclass
class TextChunk:
    text: str
    chunk_index: int


def _split_into_paragraphs(text: str) -> list[str]:
    """
    Split transcript text into paragraphs.

    Splits on:
      - Double newlines (blank lines)
      - Speaker change patterns (e.g., "Lenny:", "Brian:")
    """
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split on blank lines
    raw_paragraphs = re.split(r"\n\n+", text)

    paragraphs = []
    for p in raw_paragraphs:
        p = p.strip()
        if not p:
            continue
        # Further split on speaker turns within a paragraph
        # Speaker pattern: "Name:" at the start of a line
        speaker_splits = re.split(r"(?m)^(?=[A-Z][a-zA-Z\s]+:)", p)
        for s in speaker_splits:
            s = s.strip()
            if s:
                paragraphs.append(s)

    return paragraphs


def chunk_transcript(text: str) -> list[TextChunk]:
    """
    Chunk a transcript body into semantic chunks suitable for RAG.

    Returns a list of TextChunk objects with index and text.
    """
    paragraphs = _split_into_paragraphs(text)

    chunks: list[TextChunk] = []
    current_parts: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)

        # If adding this paragraph would exceed target size and we have content,
        # finalize the current chunk first
        if current_len + para_len > _TARGET_CHUNK_CHARS and current_parts:
            chunk_text = "\n\n".join(current_parts).strip()
            if len(chunk_text) >= _MIN_CHUNK_CHARS:
                chunks.append(TextChunk(text=chunk_text, chunk_index=len(chunks)))

            # Overlap: keep the last paragraph(s) that fit within overlap budget
            overlap_parts: list[str] = []
            overlap_len = 0
            for p in reversed(current_parts):
                if overlap_len + len(p) <= _OVERLAP_CHARS:
                    overlap_parts.insert(0, p)
                    overlap_len += len(p)
                else:
                    break

            current_parts = overlap_parts
            current_len = overlap_len

        # Handle single paragraphs that are larger than the target
        if para_len > _TARGET_CHUNK_CHARS:
            # Flush current first
            if current_parts:
                chunk_text = "\n\n".join(current_parts).strip()
                if len(chunk_text) >= _MIN_CHUNK_CHARS:
                    chunks.append(TextChunk(text=chunk_text, chunk_index=len(chunks)))
                current_parts = []
                current_len = 0

            # Split the large paragraph into sub-chunks by sentences
            sentences = re.split(r"(?<=[.!?])\s+", para)
            sub_parts: list[str] = []
            sub_len = 0
            for sent in sentences:
                if sub_len + len(sent) > _TARGET_CHUNK_CHARS and sub_parts:
                    chunk_text = " ".join(sub_parts).strip()
                    if len(chunk_text) >= _MIN_CHUNK_CHARS:
                        chunks.append(TextChunk(text=chunk_text, chunk_index=len(chunks)))
                    sub_parts = [sub_parts[-1]] if sub_parts else []
                    sub_len = len(sub_parts[0]) if sub_parts else 0
                sub_parts.append(sent)
                sub_len += len(sent)
            if sub_parts:
                chunk_text = " ".join(sub_parts).strip()
                if len(chunk_text) >= _MIN_CHUNK_CHARS:
                    chunks.append(TextChunk(text=chunk_text, chunk_index=len(chunks)))
        else:
            current_parts.append(para)
            current_len += para_len

    # Flush remaining content
    if current_parts:
        chunk_text = "\n\n".join(current_parts).strip()
        if len(chunk_text) >= _MIN_CHUNK_CHARS:
            chunks.append(TextChunk(text=chunk_text, chunk_index=len(chunks)))

    return chunks


if __name__ == "__main__":
    import sys
    sample = """
Lenny: Welcome to Lenny's Podcast. Today we're talking about product-market fit.

Brian: Thanks for having me. Product-market fit is one of the most important concepts in startups.

Lenny: How do you know when you have it?

Brian: You feel it. Users keep coming back. The retention is high. People are genuinely upset when the product is down.

Lenny: That's a great way to put it. What about the early stages?

Brian: In the early stages, you're looking for signals. Are people telling their friends? Are they using the product even when it's broken?
    """
    chunks = chunk_transcript(sample)
    print(f"Produced {len(chunks)} chunks")
    for c in chunks:
        print(f"--- Chunk {c.chunk_index} ({len(c.text)} chars) ---")
        print(c.text[:200])
