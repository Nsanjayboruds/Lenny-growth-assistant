"""
Chat agent — RAG-grounded conversational Q&A.

The agent:
  1. Retrieves relevant transcript chunks via pgvector.
  2. Builds a grounded context prompt.
  3. Calls the LLM with explicit anti-hallucination instructions.
  4. Returns the answer + source citations.

Grounding rules enforced in the system prompt:
  - Only cite what is in the retrieved context.
  - Do not fabricate quotes or URLs.
  - If evidence is insufficient, say so explicitly.
  - Distinguish retrieved evidence from editorial inference.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.providers.base import LLMMessage, LLMProvider
from app.schemas.schemas import SourceCitation
from app.services.retrieval import RetrievalService, build_context_string

logger = get_logger(__name__)


_CHAT_SYSTEM = """You are the Lenny Growth Assistant — an expert AI assistant for product managers and growth professionals.

You answer questions STRICTLY based on the transcript excerpts from Lenny's Podcast provided below.

GROUNDING RULES — Follow these exactly:
1. Only make claims that are directly supported by the provided transcript excerpts.
2. When citing evidence, attribute it clearly: "According to [Guest Name] on Lenny's Podcast..."
3. Do NOT fabricate quotes, facts, episode titles, or guest names.
4. Do NOT claim that Lenny said something unless it appears in the provided context.
5. If the transcript context does not contain enough information to answer the question, say:
   "The available Lenny's Podcast transcripts don't contain enough information to answer this question confidently. [brief explanation of what IS available if relevant]"
6. You may draw reasonable product/growth inferences from the evidence, but label them as inference:
   "Based on the evidence above, one might infer that..."
7. Keep answers focused, practical, and concise. Use bullet points or numbered lists when helpful.
8. If the question is outside the domain of product management and growth, politely redirect.

TRANSCRIPT CONTEXT:
{context}
"""

_NO_CONTEXT_RESPONSE = """I wasn't able to find relevant content in the Lenny's Podcast transcripts for your question.

This could mean:
- The topic hasn't been covered in the available episodes.
- The question is outside the scope of product management and growth.
- The knowledge base may not be fully indexed yet.

Try rephrasing your question with different keywords, or ask about a specific growth or product management topic that Lenny's guests typically discuss (e.g., product-market fit, retention, growth loops, pricing, hiring PMs, etc.)."""


@dataclass
class ChatResult:
    content: str
    sources: list[SourceCitation]
    intent: str = "CHAT"


async def run_chat(
    user_message: str,
    conversation_history: list[dict],
    provider: LLMProvider,
    db: AsyncSession,
) -> ChatResult:
    """
    Execute the RAG-grounded chat skill.

    Args:
        user_message: The current user question.
        conversation_history: List of {"role": ..., "content": ...} dicts.
        provider: The active LLM provider.
        db: Async database session.

    Returns:
        ChatResult with answer text and source citations.
    """
    # Step 1: Retrieve relevant chunks
    retrieval_service = RetrievalService(db)
    citations = await retrieval_service.retrieve(user_message)

    # Step 2: If no relevant context, return a helpful fallback
    if not citations:
        logger.info("chat.no_context", query=user_message[:80])
        return ChatResult(content=_NO_CONTEXT_RESPONSE, sources=[])

    # Step 3: Build context string
    context_str = build_context_string(citations)
    system_prompt = _CHAT_SYSTEM.format(context=context_str)

    # Step 4: Build message list (keep last 10 turns for context window management)
    messages: list[LLMMessage] = []
    for turn in conversation_history[-10:]:
        messages.append(LLMMessage(role=turn["role"], content=turn["content"]))
    messages.append(LLMMessage(role="user", content=user_message))

    # Step 5: Generate response
    logger.info("chat.generate", sources_count=len(citations))
    response = await provider.generate(
        messages=messages,
        system=system_prompt,
        max_tokens=1500,
        temperature=0.3,
    )

    return ChatResult(
        content=response.content,
        sources=citations,
        intent="CHAT",
    )
