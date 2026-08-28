"""
ingestion/parse.py — Parse transcript markdown files.

Each transcript is a markdown file with YAML frontmatter:
---
guest: Name of the guest
title: Full episode title
youtube_url: https://...
video_id: abc123
publish_date: 2023-01-01
description: Episode description
duration_seconds: 3600
duration: 1:00:00
view_count: 100000
channel: Lenny's Podcast
---

[Full transcript text follows]
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ParsedTranscript:
    slug: str                          # folder name, e.g. "brian-chesky"
    guest: str
    title: str
    youtube_url: Optional[str] = None
    video_id: Optional[str] = None
    publish_date: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[str] = None
    body: str = ""                     # full transcript text


def _extract_frontmatter(content: str) -> tuple[dict, str]:
    """
    Split YAML frontmatter from markdown body.
    Returns (metadata_dict, body_text).
    """
    # Match --- ... --- at the start of the file
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content

    raw_yaml = match.group(1)
    body = match.group(2).strip()

    try:
        metadata = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError:
        metadata = {}

    return metadata, body


def _normalize_text(text: str) -> str:
    """Normalize whitespace and clean up transcript text."""
    # Remove excessive blank lines (3+ → 2)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove markdown link syntax but keep text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove bare URLs
    text = re.sub(r"https?://\S+", "", text)
    # Strip leading/trailing whitespace
    return text.strip()


def parse_transcript(file_path: Path, slug: str) -> Optional[ParsedTranscript]:
    """
    Parse a single transcript.md file.

    Returns None if the file cannot be parsed (logs the issue).
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"[parse] Cannot read {file_path}: {e}")
        return None

    metadata, body = _extract_frontmatter(content)

    if not body.strip():
        print(f"[parse] Empty body in {file_path}, skipping.")
        return None

    guest = str(metadata.get("guest", slug)).strip()
    title = str(metadata.get("title", slug)).strip()

    return ParsedTranscript(
        slug=slug,
        guest=guest,
        title=title,
        youtube_url=metadata.get("youtube_url"),
        video_id=metadata.get("video_id"),
        publish_date=str(metadata.get("publish_date", "")) or None,
        description=metadata.get("description"),
        duration=metadata.get("duration"),
        body=_normalize_text(body),
    )


def load_all_transcripts(repo_dir: str) -> list[ParsedTranscript]:
    """
    Walk the episodes/ directory and parse all transcript.md files.

    Returns a list of ParsedTranscript objects.
    """
    episodes_dir = Path(repo_dir) / "episodes"
    if not episodes_dir.is_dir():
        print(f"[parse] Episodes directory not found: {episodes_dir}")
        return []

    transcripts = []
    episode_dirs = sorted(episodes_dir.iterdir())

    for ep_dir in episode_dirs:
        if not ep_dir.is_dir():
            continue
        transcript_file = ep_dir / "transcript.md"
        if not transcript_file.is_file():
            print(f"[parse] No transcript.md in {ep_dir.name}, skipping.")
            continue

        parsed = parse_transcript(transcript_file, ep_dir.name)
        if parsed:
            transcripts.append(parsed)

    print(f"[parse] Loaded {len(transcripts)} transcripts from {episodes_dir}")
    return transcripts


if __name__ == "__main__":
    import sys
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "./lennys-podcast-transcripts"
    transcripts = load_all_transcripts(repo_path)
    if transcripts:
        t = transcripts[0]
        print(f"Example: {t.slug} | {t.title} | {t.guest}")
        print(f"Body preview: {t.body[:200]}...")
