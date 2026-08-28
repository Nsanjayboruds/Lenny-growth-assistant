"""
Intent router — classifies user messages into one of three skills:
  CHAT      — standard grounded Q&A
  SHIP30    — generate a Ship 30 for 30 essay
  ARTIFACT  — generate a Markdown or HTML artifact
"""
from __future__ import annotations

import re
from enum import Enum

from app.logging_config import get_logger
from app.providers.base import LLMMessage, LLMProvider

logger = get_logger(__name__)


class Intent(str, Enum):
    CHAT = "CHAT"
    SHIP30 = "SHIP30"
    ARTIFACT = "ARTIFACT"


# Fast keyword-based pre-check before calling the LLM
_SHIP30_KEYWORDS = [
    r"\bship\s*30\b",
    r"\bessay\b",
    r"\bnewsletter\b",
    r"\bdigital\s+article\b",
    r"\bwrite\s+(an?|a\s+\w+)?\s*(essay|post|article|thread)\b",
    r"\bturn\s+this\s+into\b",
    r"\bconvert\s+this\b",
]

_ARTIFACT_KEYWORDS = [
    r"\bcreate\s+(a|an|an?\s+\w+)?\s*(landing\s+page|page|dashboard|report|document|template)\b",
    r"\bgenerate\s+(a|an|an?\s+\w+)?\s*(html|markdown|webpage|landing)\b",
    r"\bbuild\s+(a|an|an?\s+\w+)?\s*(page|template|dashboard|landing)\b",
    r"\blanding\s+page\b",
    r"\bhtml\s+(?:page|artifact|document|landing)\b",
    r"\bmarkdown\s+(artifact|document|report)\b",
    r"\bhtml\s+(artifact|document)\b",
    r"\bformatted\s+(document|report|page)\b",
    r"\ban\s+html\b",  # 'Create an HTML ...'
]


def _keyword_classify(text: str) -> Intent | None:
    """
    Quick keyword-based intent detection.
    Returns None if ambiguous, so LLM routing is used as fallback.
    """
    lower = text.lower()
    for pattern in _SHIP30_KEYWORDS:
        if re.search(pattern, lower):
            return Intent.SHIP30
    for pattern in _ARTIFACT_KEYWORDS:
        if re.search(pattern, lower):
            return Intent.ARTIFACT
    return None


_ROUTER_SYSTEM = """You are an intent classifier for the Lenny Growth Assistant.

Classify the user message into exactly ONE of these intents:
  CHAT     — The user wants to ask a product/growth question or have a conversation.
  SHIP30   — The user wants to generate a Ship 30 for 30 style essay or article.
  ARTIFACT — The user wants to generate a formatted artifact (Markdown doc, HTML page, landing page, report).

Respond with ONLY the intent label: CHAT, SHIP30, or ARTIFACT.
Do not explain your choice. Do not add punctuation.
"""


async def route_intent(
    user_message: str,
    provider: LLMProvider,
    conversation_context: str = "",
) -> Intent:
    """
    Determine the user's intent.

    Uses fast keyword matching first; falls back to LLM classification
    for ambiguous cases. Defaults to CHAT on any error.
    """
    # Fast path
    keyword_result = _keyword_classify(user_message)
    if keyword_result is not None:
        logger.info("router.keyword_match", intent=keyword_result, message=user_message[:80])
        return keyword_result

    # LLM path
    context_snippet = f"\nRecent conversation:\n{conversation_context[:500]}" if conversation_context else ""
    messages = [
        LLMMessage(
            role="user",
            content=f"Message to classify:{context_snippet}\n\nUser: {user_message}"
        )
    ]

    try:
        response = await provider.generate(
            messages=messages,
            system=_ROUTER_SYSTEM,
            max_tokens=10,
            temperature=0.0,
        )
        raw = response.content.strip().upper()
        intent = Intent(raw) if raw in Intent.__members__ else Intent.CHAT
    except Exception as e:
        logger.warning("router.llm_failed", error=str(e))
        intent = Intent.CHAT

    logger.info("router.classified", intent=intent, message=user_message[:80])
    return intent
