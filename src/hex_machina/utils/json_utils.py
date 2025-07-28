import json
import re

# Import content extraction libraries with fallbacks
try:
    from main_content_extractor import MainContentExtractor

    MAIN_CONTENT_EXTRACTOR_AVAILABLE = True
except ImportError:
    MAIN_CONTENT_EXTRACTOR_AVAILABLE = False

try:
    import trafilatura

    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

try:
    from readability import Document

    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False


def make_json_safe(val):
    """Ensure a value is JSON serializable, otherwise return its string representation."""
    try:
        json.dumps(val)
        return val
    except Exception:
        return str(val)


def _clean_markdown(text: str) -> str:
    """Clean and normalize markdown text.

    Args:
        text: Raw markdown text

    Returns:
        Cleaned markdown text
    """
    if not text:
        return ""

    try:
        # Remove URLs but preserve surrounding spaces
        text = re.sub(r"\s*(https?:\/\/|www\.)([\w\.\/-]+)\s*", " ", text)

        # Remove images but preserve alt text if present
        text = re.sub(r"!\[([^\]]*?)\]\(.*?\)", r"\1", text, flags=re.DOTALL)

        # Remove remaining links but keep the link text
        text = re.sub(r"\[([^\]]*?)\]\(.*?\)", r"\1", text, flags=re.DOTALL)

        # Fix dashes separated by line breaks (e.g., "-\nword" → "-word")
        text = re.sub(r"(-)\n(\w)", r"\1\2", text)

        # Fix markdown bullet lists - preserve the asterisk and proper formatting
        # Use MULTILINE flag to match start of lines
        text = re.sub(r"^(\s*)\*(\s*)", r"\1* ", text, flags=re.MULTILINE)

        # Fix markdown numbered lists - preserve the numbering and proper formatting
        text = re.sub(r"^(\s*)(\d+\.)(\s*)", r"\1\2 ", text, flags=re.MULTILINE)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Decode HTML entities properly
        text = re.sub(r"&nbsp;", " ", text)  # Replace &nbsp; with space
        text = re.sub(r"&amp;", "&", text)  # Replace &amp; with &
        text = re.sub(r"&lt;", "<", text)  # Replace &lt; with <
        text = re.sub(r"&gt;", ">", text)  # Replace &gt; with >
        text = re.sub(r"&quot;", '"', text)  # Replace &quot; with "
        text = re.sub(r"&#39;", "'", text)  # Replace &#39; with '

        # Remove lines that are only whitespace, asterisks, or hash symbols
        # But be more careful - only remove if the line is truly empty of content
        text = re.sub(
            r"\n[ \t]*\*[ \t]*\n", "\n", text
        )  # Remove lines with just asterisks
        text = re.sub(
            r"\n[ \t]*#[ \t]*\n", "\n", text
        )  # Remove lines with just hash symbols

        # Normalize whitespace and line breaks
        text = re.sub(r"\n{3,}", "\n\n", text)  # Collapse 3+ newlines to 2
        text = re.sub(r"[ \t]+", " ", text)  # Collapse multiple spaces/tabs

        return text.strip()

    except Exception:
        # Fallback to basic cleaning if regex operations fail
        return text.strip()


def extract_markdown_from_html(html: str) -> str:
    """Extract main content from HTML as markdown.

    Args:
        html: HTML string to process

    Returns:
        Extracted markdown content

    Raises:
        ImportError: If no content extraction library is available
    """
    if not html:
        return ""

    # Try Trafilatura first (best overall)
    if TRAFILATURA_AVAILABLE:
        try:
            extracted = trafilatura.extract(
                html, include_formatting=True, include_links=True
            )
            if extracted:
                return _clean_markdown(extracted)
        except Exception:
            pass

    # Try Readability as fallback
    if READABILITY_AVAILABLE:
        try:
            doc = Document(html)
            extracted = doc.summary()
            if extracted:
                return _clean_markdown(extracted)
        except Exception:
            pass

    # Try MainContentExtractor as last resort
    if MAIN_CONTENT_EXTRACTOR_AVAILABLE:
        try:
            extracted = MainContentExtractor.extract(html, output_format="markdown")
            if extracted:
                return _clean_markdown(extracted)
        except Exception:
            pass

    # If no extraction library is available
    if not any(
        [
            TRAFILATURA_AVAILABLE,
            READABILITY_AVAILABLE,
            MAIN_CONTENT_EXTRACTOR_AVAILABLE,
        ]
    ):
        raise ImportError(
            "No content extraction library available. Please install one of: "
            "trafilatura, readability-lxml, or MainContentExtractor"
        )

    # Fallback: basic HTML cleaning
    return _clean_markdown(html)
