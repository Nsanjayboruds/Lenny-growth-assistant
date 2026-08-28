"""
HTML Sanitizer — strips dangerous content from LLM-generated HTML artifacts.

Security Model:
  ALLOWED: Structural HTML, styling, text formatting, links (http/https only)
  BLOCKED: Scripts, iframes, forms, event handlers (on*), data: URIs,
           javascript: hrefs, meta refreshes, object/embed elements

The sanitized HTML is rendered inside a sandboxed iframe:
  sandbox="allow-same-origin"
  — Allows CSS to apply (same-origin needed for stylesheets)
  — Blocks JS execution (no allow-scripts)
  — Blocks form submission (no allow-forms)
  — Blocks navigation (no allow-top-navigation)
  — Blocks popups (no allow-popups)

Limitations:
  — CSS within <style> tags is NOT fully sanitized (complex to parse).
    Mitigation: the sandboxed iframe prevents CSS-based attacks from
    affecting the parent frame.
  — Mutation XSS via nested HTML parsers is mitigated by bleach's
    consistent use of html5lib.
"""
from __future__ import annotations

import re

import bleach
from bleach.css_sanitizer import CSSSanitizer

# Tags that are safe for rendered HTML artifacts
ALLOWED_TAGS = [
    # Structure
    "html", "head", "body", "title",
    # Headings
    "h1", "h2", "h3", "h4", "h5", "h6",
    # Text
    "p", "br", "hr", "strong", "b", "em", "i", "u", "s", "del",
    "code", "pre", "blockquote", "q", "cite", "abbr", "mark",
    "small", "sup", "sub",
    # Lists
    "ul", "ol", "li", "dl", "dt", "dd",
    # Links
    "a",
    # Media (no src allowed — src is filtered in attrs)
    "img",
    # Tables
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption", "colgroup", "col",
    # Layout
    "div", "span", "section", "article", "header", "footer", "nav",
    "main", "aside", "figure", "figcaption",
    # Styling
    "style",
    # Meta (allowed but with restricted attrs)
    "meta",
]

# Attributes that are safe (no event handlers, no javascript:)
ALLOWED_ATTRIBUTES = {
    "*": ["class", "id", "title", "aria-label", "aria-hidden", "role",
          "data-*", "style"],
    "a": ["href", "target", "rel", "class", "id"],
    "img": ["alt", "class", "id"],  # src is intentionally NOT allowed
    "td": ["colspan", "rowspan", "class", "id"],
    "th": ["colspan", "rowspan", "scope", "class", "id"],
    "col": ["span"],
    "meta": ["charset", "name"],  # 'content' excluded to block meta refresh attacks
    "style": [],
}

# Allowed CSS properties in inline style attributes
ALLOWED_CSS_PROPERTIES = [
    "color", "background-color", "background", "font-size", "font-weight",
    "font-family", "font-style", "text-align", "text-decoration",
    "margin", "margin-top", "margin-bottom", "margin-left", "margin-right",
    "padding", "padding-top", "padding-bottom", "padding-left", "padding-right",
    "border", "border-radius", "border-color", "border-width",
    "display", "flex", "flex-direction", "align-items", "justify-content",
    "gap", "grid", "grid-template-columns", "grid-template-rows",
    "width", "max-width", "min-width", "height", "max-height", "min-height",
    "overflow", "position", "top", "left", "right", "bottom",
    "opacity", "box-shadow", "line-height", "letter-spacing",
    "list-style", "list-style-type",
]

# Protocols allowed in href attributes
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

# Dangerous patterns to strip from <style> blocks
_DANGEROUS_CSS_PATTERNS = [
    re.compile(r"expression\s*\(", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"@import", re.IGNORECASE),
    re.compile(r"behavior\s*:", re.IGNORECASE),
    re.compile(r"-moz-binding", re.IGNORECASE),
]


def _clean_style_tags(html: str) -> str:
    """Strip dangerous patterns from <style> blocks."""
    def sanitize_style(match: re.Match) -> str:
        content = match.group(1)
        for pattern in _DANGEROUS_CSS_PATTERNS:
            content = pattern.sub("/* removed */", content)
        return f"<style>{content}</style>"

    return re.sub(r"<style>(.*?)</style>", sanitize_style, html, flags=re.DOTALL | re.IGNORECASE)


def sanitize_html(html: str) -> str:
    """
    Sanitize HTML from an untrusted LLM-generated source.

    Steps:
      1. Strip dangerous CSS patterns from <style> blocks.
      2. Run bleach to remove disallowed tags and attributes.
      3. Enforce allowed link protocols.

    Returns safe HTML ready to render in a sandboxed iframe.
    """
    # Step 1: Clean style tags
    html = _clean_style_tags(html)

    css_sanitizer = CSSSanitizer(allowed_css_properties=ALLOWED_CSS_PROPERTIES)

    # Step 2: bleach clean
    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=css_sanitizer,
        strip=True,
        strip_comments=True,
    )

    return cleaned


def sanitize_for_iframe(html: str) -> str:
    """
    Prepare sanitized HTML for rendering inside a sandboxed iframe.
    Wraps bare HTML fragments in a full document if needed.
    """
    sanitized = sanitize_html(html)

    # If it's already a full document, return as-is
    if "<html" in sanitized.lower() and "<body" in sanitized.lower():
        return sanitized

    # Wrap fragment in a minimal document
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      line-height: 1.6;
      color: #1a1a2e;
      background: #ffffff;
      padding: 1.5rem;
      margin: 0;
    }}
    h1, h2, h3 {{ color: #6c63ff; }}
    a {{ color: #6c63ff; }}
    code {{ background: #f0f0f0; padding: 0.2em 0.4em; border-radius: 3px; }}
    pre {{ background: #f0f0f0; padding: 1rem; border-radius: 6px; overflow-x: auto; }}
  </style>
</head>
<body>
{sanitized}
</body>
</html>"""
