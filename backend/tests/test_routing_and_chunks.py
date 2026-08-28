"""
Tests for the intent router.
"""
import pytest
from app.agents.router import Intent, _keyword_classify


class TestKeywordRouter:
    """Test the fast keyword-based intent classification."""

    def test_normal_question_is_chat(self):
        assert _keyword_classify("What does Lenny say about product-market fit?") is None

    def test_ship30_keyword(self):
        assert _keyword_classify("Write a ship 30 essay about growth loops") == Intent.SHIP30

    def test_essay_keyword(self):
        assert _keyword_classify("Write an essay about retention") == Intent.SHIP30

    def test_newsletter_keyword(self):
        assert _keyword_classify("Write a newsletter post about my conversation") == Intent.SHIP30

    def test_artifact_html_keyword(self):
        assert _keyword_classify("Create an HTML landing page for my framework") == Intent.ARTIFACT

    def test_artifact_landing_page(self):
        assert _keyword_classify("Build a landing page based on this conversation") == Intent.ARTIFACT

    def test_artifact_markdown_keyword(self):
        assert _keyword_classify("Generate a markdown document summarizing this") == Intent.ARTIFACT

    def test_ambiguous_returns_none(self):
        # These should return None (fall through to LLM classification)
        assert _keyword_classify("What are the best growth metrics?") is None
        assert _keyword_classify("How do I build a growth team?") is None

    def test_case_insensitive(self):
        assert _keyword_classify("WRITE AN ESSAY about growth") == Intent.SHIP30
        assert _keyword_classify("CREATE A LANDING PAGE") == Intent.ARTIFACT


class TestChunker:
    """Test the transcript chunker."""

    def test_chunker_produces_chunks(self):
        from ingestion.chunk import chunk_transcript
        text = "Lenny: Hello.\n\n" * 50  # Repeat to get multiple chunks
        chunks = chunk_transcript(text)
        assert len(chunks) > 0

    def test_chunker_assigns_sequential_indices(self):
        from ingestion.chunk import chunk_transcript
        text = "\n\n".join([f"Paragraph {i}. " * 30 for i in range(20)])
        chunks = chunk_transcript(text)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunker_respects_min_length(self):
        from ingestion.chunk import chunk_transcript
        # Very short text should produce no chunks (below MIN_CHUNK_CHARS)
        chunks = chunk_transcript("Hi.")
        assert len(chunks) == 0

    def test_chunker_handles_empty_text(self):
        from ingestion.chunk import chunk_transcript
        chunks = chunk_transcript("")
        assert chunks == []


class TestTranscriptParser:
    """Test the transcript parser."""

    def test_parse_frontmatter(self):
        from ingestion.parse import _extract_frontmatter
        content = "---\nguest: Brian Chesky\ntitle: Test Episode\n---\nBody text here."
        meta, body = _extract_frontmatter(content)
        assert meta.get("guest") == "Brian Chesky"
        assert meta.get("title") == "Test Episode"
        assert body == "Body text here."

    def test_parse_no_frontmatter(self):
        from ingestion.parse import _extract_frontmatter
        content = "Just body text with no frontmatter."
        meta, body = _extract_frontmatter(content)
        assert meta == {}
        assert "Just body text" in body

    def test_normalize_text(self):
        from ingestion.parse import _normalize_text
        text = "Word  \n\n\n\n\nToo many newlines\n\nBack to normal"
        result = _normalize_text(text)
        assert "\n\n\n" not in result
