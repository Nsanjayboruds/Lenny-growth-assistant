"""
Artifact generation agent — creates Markdown or HTML/CSS artifacts
based on the current conversation and transcript evidence.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.providers.base import LLMMessage, LLMProvider
from app.schemas.schemas import SourceCitation
from app.services.retrieval import RetrievalService, build_context_string
from app.services.sanitizer import sanitize_for_iframe

logger = get_logger(__name__)


_ARTIFACT_SYSTEM_MARKDOWN = """You are the Lenny Growth Assistant artifact generator.

Your task is to generate a well-structured Markdown document based on the conversation context and transcript evidence.

RULES:
1. Produce ONLY the Markdown content — no explanation, no preamble.
2. Use proper Markdown: # headings, ## subheadings, **bold**, *italic*, bullet lists, tables.
3. Ground claims in transcript evidence where possible.
4. Include a ## Sources section at the end if transcript evidence was used.
5. Make the document professional, useful, and actionable.

TRANSCRIPT EVIDENCE:
{context}
"""

_ARTIFACT_SYSTEM_HTML = """You are the Lenny Growth Assistant artifact generator.

Your task is to generate a complete, beautiful HTML/CSS page based on the conversation context.

RULES:
1. Produce ONLY the HTML — no explanation, no markdown fences, no preamble.
2. Start with <!DOCTYPE html> and include a full <head> with styles.
3. Use modern CSS (flexbox, CSS custom properties, clean typography).
4. Use a professional color palette — purples, deep blues, or clean neutrals.
5. Include all CSS inline in a <style> tag — no external resources.
6. Ground content claims in transcript evidence where possible.
7. Make it visually impressive and functional.
8. DO NOT include JavaScript — pure HTML/CSS only.
9. Include a sources section if using transcript evidence.

TRANSCRIPT EVIDENCE:
{context}
"""

_INSUFFICIENT_ARTIFACT = """# Insufficient Context

I couldn't generate a meaningful artifact because:
- Not enough transcript evidence was found for this topic.
- The conversation doesn't provide enough context for the artifact.

**Try:**
1. Have a conversation about the topic first.
2. Then request the artifact based on that discussion.
"""


@dataclass
class ArtifactResult:
    content: str
    sanitized_content: str
    artifact_type: str
    title: str
    sources: list[SourceCitation]
    intent: str = "ARTIFACT"


def _detect_artifact_type(user_message: str) -> str:
    """Detect whether user wants HTML or Markdown artifact."""
    lower = user_message.lower()
    if any(kw in lower for kw in ["html", "landing page", "webpage", "web page", "website"]):
        return "html"
    return "markdown"


def _extract_title(user_message: str, artifact_type: str) -> str:
    """Generate a title for the artifact from the user request."""
    # Simple heuristic: use first 60 chars of the request
    base = user_message.strip()[:60].rstrip(".,?!")
    suffix = " (HTML)" if artifact_type == "html" else " (Markdown)"
    return base + suffix


async def run_artifact(
    user_message: str,
    conversation_history: list[dict],
    provider: LLMProvider,
    db: AsyncSession,
) -> ArtifactResult:
    """
    Generate a Markdown or HTML artifact based on conversation + transcript evidence.
    """
    artifact_type = _detect_artifact_type(user_message)
    title = _extract_title(user_message, artifact_type)

    # Build search query from conversation
    recent_topics = " ".join(
        turn["content"][:150]
        for turn in conversation_history[-4:]
        if turn["role"] in ("user", "assistant")
    )
    search_query = f"{user_message} {recent_topics}"[:400]

    # Retrieve transcript evidence
    retrieval_service = RetrievalService(db)
    citations = await retrieval_service.retrieve(search_query)
    context_str = build_context_string(citations) if citations else "No specific transcript evidence available."

    # Build system prompt
    if artifact_type == "html":
        system_prompt = _ARTIFACT_SYSTEM_HTML.format(context=context_str)
    else:
        system_prompt = _ARTIFACT_SYSTEM_MARKDOWN.format(context=context_str)

    # Build messages
    messages: list[LLMMessage] = []
    for turn in conversation_history[-4:]:
        messages.append(LLMMessage(role=turn["role"], content=turn["content"]))

    artifact_request = (
        f"{user_message}\n\n"
        f"Generate a {'complete HTML page' if artifact_type == 'html' else 'Markdown document'} "
        "for this request. Use the transcript evidence from the system prompt. "
        "Produce ONLY the artifact content — nothing else."
    )
    messages.append(LLMMessage(role="user", content=artifact_request))

    logger.info("artifact.generate", artifact_type=artifact_type, sources_count=len(citations))
    response = await provider.generate(
        messages=messages,
        system=system_prompt,
        max_tokens=3000,
        temperature=0.5,
    )

    raw_content = response.content.strip()

    # Strip markdown code fences if LLM wrapped the output
    if raw_content.startswith("```html"):
        raw_content = raw_content[7:]
    elif raw_content.startswith("```markdown"):
        raw_content = raw_content[11:]
    elif raw_content.startswith("```"):
        raw_content = raw_content[3:]
    if raw_content.endswith("```"):
        raw_content = raw_content[:-3]
    raw_content = raw_content.strip()

    # Sanitize HTML; Markdown is left as-is
    if artifact_type == "html":
        sanitized = sanitize_for_iframe(raw_content)
    else:
        sanitized = raw_content  # Markdown rendered client-side is safe

    return ArtifactResult(
        content=raw_content,
        sanitized_content=sanitized,
        artifact_type=artifact_type,
        title=title,
        sources=citations,
        intent="ARTIFACT",
    )
