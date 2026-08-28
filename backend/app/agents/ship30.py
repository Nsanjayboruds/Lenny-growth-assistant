"""
Ship 30 for 30 essay generation agent.

Generates a ~1,250-word essay grounded in Lenny's Podcast transcripts,
following Ship 30 for 30 digital writing principles.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.providers.base import LLMMessage, LLMProvider
from app.schemas.schemas import SourceCitation
from app.services.retrieval import RetrievalService, build_context_string

logger = get_logger(__name__)

# Load Ship 30 principles from the skills directory
_SKILLS_DIR = pathlib.Path(__file__).parent.parent.parent.parent.parent / "skills" / "ship30"


def _load_skill_file(filename: str) -> str:
    """Load a skill file, returning empty string if not found."""
    path = _SKILLS_DIR / filename
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("ship30.skill_file_missing", file=str(path))
        return ""


_PRINCIPLES = _load_skill_file("principles.md")
_TEMPLATE = _load_skill_file("template.md")


_SHIP30_SYSTEM = """You are the Lenny Growth Assistant — an expert essay writer using the Ship 30 for 30 digital writing methodology.

Your task is to write a ~1,250-word essay (minimum 1,100, maximum 1,350 words) grounded in Lenny's Podcast transcripts.

## Ship 30 for 30 Principles You Must Follow

{principles}

## Essay Template to Use

{template}

## GROUNDING RULES — Follow These Exactly

1. Every major claim MUST be supported by the transcript evidence provided below.
2. Attribute evidence clearly: "According to [Guest Name] on Lenny's Podcast, ..."
3. Do NOT fabricate quotes or make up what guests said.
4. If transcript evidence is insufficient for a section, say so briefly and fill with clearly labeled inference.
5. Include a "Sources" section at the end listing the episodes used.
6. AIM for exactly 1,250 words. Count carefully.

## TRANSCRIPT EVIDENCE

{context}
"""

_NO_CONTEXT_SHIP30 = """## Insufficient Transcript Evidence

I couldn't find enough relevant content in Lenny's Podcast transcripts to write a grounded Ship 30 essay on this topic.

To generate a well-grounded essay, please:
1. Ask a question in the chat first so relevant transcripts are identified.
2. Then request the essay based on that conversation.

Or try asking about a topic with more coverage in Lenny's library, such as:
- Product-market fit
- Growth loops and retention
- Building and hiring product teams
- Pricing strategy
- Product strategy frameworks"""


@dataclass
class Ship30Result:
    content: str
    sources: list[SourceCitation]
    intent: str = "SHIP30"


async def run_ship30(
    user_message: str,
    conversation_history: list[dict],
    provider: LLMProvider,
    db: AsyncSession,
) -> Ship30Result:
    """
    Generate a Ship 30 for 30 essay grounded in Lenny's Podcast transcripts.

    Derives the essay topic from the conversation context and current message.
    """
    # Build a rich query from the conversation to retrieve relevant chunks
    # Use last few conversation turns to understand the essay topic
    recent_topics = " ".join(
        turn["content"][:200]
        for turn in conversation_history[-6:]
        if turn["role"] in ("user", "assistant")
    )
    search_query = f"{user_message} {recent_topics}"[:500]

    # Retrieve relevant transcript chunks
    retrieval_service = RetrievalService(db)
    citations = await retrieval_service.retrieve(search_query)

    if not citations:
        logger.info("ship30.no_context", query=search_query[:80])
        return Ship30Result(content=_NO_CONTEXT_SHIP30, sources=[])

    context_str = build_context_string(citations)

    # Build the system prompt with principles and template
    system_prompt = _SHIP30_SYSTEM.format(
        principles=_PRINCIPLES,
        template=_TEMPLATE,
        context=context_str,
    )

    # Build conversation context for the essay request
    messages: list[LLMMessage] = []
    for turn in conversation_history[-6:]:
        messages.append(LLMMessage(role=turn["role"], content=turn["content"]))

    essay_request = (
        f"{user_message}\n\n"
        "Please write a Ship 30 for 30 style essay (~1,250 words) on this topic, "
        "grounded in the transcript evidence provided in the system prompt. "
        "Include proper H2 section headings, short paragraphs, and a Sources section."
    )
    messages.append(LLMMessage(role="user", content=essay_request))

    logger.info("ship30.generate", sources_count=len(citations))
    response = await provider.generate(
        messages=messages,
        system=system_prompt,
        max_tokens=2500,
        temperature=0.6,
    )

    return Ship30Result(
        content=response.content,
        sources=citations,
        intent="SHIP30",
    )
