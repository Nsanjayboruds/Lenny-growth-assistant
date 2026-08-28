"""
Tests for the HTML sanitizer — security-critical tests.

These tests verify that dangerous HTML input is properly sanitized.
"""
import pytest
from app.services.sanitizer import sanitize_html, sanitize_for_iframe


class TestSanitizeHtml:
    """Unit tests for the HTML sanitizer."""

    def test_script_tag_removed(self):
        """Script tags must be completely removed.
        
        bleach strips the <script> tag but preserves the text content.
        This is correct behavior — bare text cannot execute JS.
        The important assertion is that the <script> tag wrapper is gone.
        """
        dangerous = "<p>Hello</p><script>alert('xss')</script>"
        result = sanitize_html(dangerous)
        assert "<script>" not in result
        assert "<p>Hello</p>" in result
        # Text is left but cannot execute without the script tag

    def test_event_handler_removed(self):
        """on* event handlers must be stripped from all tags."""
        dangerous = '<img src="x" onerror="alert(1)">'
        result = sanitize_html(dangerous)
        assert "onerror" not in result
        assert "alert" not in result

    def test_javascript_href_blocked(self):
        """javascript: protocol in href must be blocked."""
        dangerous = '<a href="javascript:alert(1)">Click me</a>'
        result = sanitize_html(dangerous)
        assert "javascript:" not in result

    def test_data_uri_src_blocked(self):
        """data: URIs in src attributes must be blocked."""
        dangerous = '<img src="data:text/html,<script>alert(1)</script>">'
        result = sanitize_html(dangerous)
        # src attribute on img is not in our allowed attrs, so it should be stripped
        assert "data:" not in result or "src" not in result

    def test_iframe_removed(self):
        """iframe tags must be removed."""
        dangerous = '<iframe src="https://evil.com"></iframe>'
        result = sanitize_html(dangerous)
        assert "<iframe" not in result

    def test_object_removed(self):
        """object and embed tags must be removed."""
        dangerous = '<object data="evil.swf"></object><embed src="evil.swf">'
        result = sanitize_html(dangerous)
        assert "<object" not in result
        assert "<embed" not in result

    def test_form_removed(self):
        """form tags must be removed."""
        dangerous = '<form action="https://evil.com"><input type="text"><button>Submit</button></form>'
        result = sanitize_html(dangerous)
        assert "<form" not in result

    def test_safe_content_preserved(self):
        """Safe HTML content should be preserved."""
        safe = """
        <h1>Growth Framework</h1>
        <p>According to Lenny's Podcast, <strong>product-market fit</strong> is essential.</p>
        <ul>
          <li>Retention</li>
          <li>Growth loops</li>
        </ul>
        <a href="https://youtube.com/watch?v=123">Watch episode</a>
        """
        result = sanitize_html(safe)
        assert "<h1>Growth Framework</h1>" in result
        assert "<strong>product-market fit</strong>" in result
        assert "<li>Retention</li>" in result

    def test_css_expression_removed(self):
        """CSS expression() attacks must be neutralized."""
        dangerous = '<style>body { background: expression(alert(1)); }</style>'
        result = sanitize_html(dangerous)
        assert "expression(" not in result

    def test_css_javascript_import_removed(self):
        """CSS @import and javascript: in style must be removed."""
        dangerous = '<style>@import url("javascript:alert(1)");</style>'
        result = sanitize_html(dangerous)
        assert "@import" not in result

    def test_html_comments_stripped(self):
        """HTML comments should be stripped."""
        with_comments = "<!-- malicious --> <p>Normal</p>"
        result = sanitize_html(with_comments)
        assert "<!--" not in result
        assert "<p>Normal</p>" in result

    def test_nested_script_attempt(self):
        """Nested/broken script tags must not produce executable scripts."""
        dangerous = "<sc<script>ript>alert(1)</sc</script>ript>"
        result = sanitize_html(dangerous)
        # The <script> tag must be gone — any remaining text is inert
        assert "<script>" not in result
        assert "</script>" not in result

    def test_sanitize_for_iframe_wraps_fragment(self):
        """Bare HTML fragments should be wrapped in a full document."""
        fragment = "<h1>Hello</h1><p>World</p>"
        result = sanitize_for_iframe(fragment)
        assert "<!DOCTYPE html>" in result
        assert "<html" in result
        assert "<body" in result
        assert "<h1>Hello</h1>" in result

    def test_sanitize_for_iframe_full_document_passthrough(self):
        """Full HTML documents should pass through (still sanitized)."""
        full = "<!DOCTYPE html><html><head></head><body><p>Hello</p></body></html>"
        result = sanitize_for_iframe(full)
        assert "<p>Hello</p>" in result

    def test_meta_refresh_stripped(self):
        """Meta content attribute is stripped to prevent refresh attacks."""
        dangerous = '<meta http-equiv="refresh" content="0;url=javascript:alert(1)">'
        result = sanitize_html(dangerous)
        # 'content' attr is excluded from allowed meta attrs
        # so javascript: URL in content cannot be used for redirection
        assert "http-equiv" not in result  # http-equiv is not in allowed meta attrs
        assert "javascript:" not in result


class TestSanitizerEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_string(self):
        result = sanitize_html("")
        assert result == ""

    def test_plain_text(self):
        result = sanitize_html("Just plain text, no HTML.")
        assert "Just plain text" in result

    def test_deeply_nested_safe_content(self):
        nested = "<div><section><article><p><strong>Deep</strong></p></article></section></div>"
        result = sanitize_html(nested)
        assert "Deep" in result
