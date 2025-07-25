"""Article parser for cleaning and extracting data from scraped content."""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

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


class ArticleParser:
    """Parser for cleaning and extracting article data."""

    def parse_title(self, raw_title: str) -> str:
        """Parse and clean article title.

        Args:
            raw_title: Raw title from RSS or scraped content

        Returns:
            Cleaned title
        """
        if not raw_title:
            return ""

        # Remove extra whitespace and newlines
        title = re.sub(r"\s+", " ", raw_title.strip())
        return title

    def parse_author(self, raw_author: str) -> str:
        """Parse and clean article author.

        Args:
            raw_author: Raw author information

        Returns:
            Cleaned author name
        """
        if not raw_author:
            return ""

        # Remove extra whitespace and common prefixes
        author = re.sub(r"\s+", " ", raw_author.strip())
        author = re.sub(r"^by\s+", "", author, flags=re.IGNORECASE)
        return author

    def parse_url(self, raw_url: str) -> str:
        """Parse and clean article URL.

        Args:
            raw_url: Raw URL from RSS or scraped content

        Returns:
            Cleaned URL
        """
        if not raw_url:
            return ""

        return raw_url.strip()

    def parse_url_domain(self, raw_url: str) -> str:
        """Extract domain from URL.

        Args:
            raw_url: Article URL

        Returns:
            Domain name
        """
        try:
            parsed = urlparse(raw_url)
            return parsed.netloc
        except Exception:
            return ""

    def parse_published_date(self, raw_date: str) -> Optional[datetime]:
        """Parse published date from various formats.

        Args:
            raw_date: Raw date string

        Returns:
            Parsed datetime in UTC, or None if parsing fails
        """
        from src.hex_machina.utils import DateParser

        return DateParser.parse_date(raw_date)

    def parse_summary(self, raw_summary: str) -> str:
        """Parse and clean article summary.

        Args:
            raw_summary: Raw summary from RSS or scraped content

        Returns:
            Cleaned summary
        """
        if not raw_summary:
            return ""

        # Remove HTML tags and extra whitespace
        summary = re.sub(r"<[^>]+>", "", raw_summary)
        summary = re.sub(r"\s+", " ", summary.strip())
        return summary

    def parse_tags(self, raw_tags: str) -> list[str]:
        """Parse and clean article tags.

        Args:
            raw_tags: Raw tags from RSS or scraped content

        Returns:
            List of cleaned tags
        """
        if not raw_tags:
            return []

        tags = [tag["term"].strip() for tag in raw_tags]
        return tags

    def _clean_markdown(self, text: str) -> str:
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

    def _extract_markdown_from_html(self, html: str) -> str:
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
                    return self._clean_markdown(extracted)
            except Exception:
                pass

        # Try Readability as fallback
        if READABILITY_AVAILABLE:
            try:
                doc = Document(html)
                extracted = doc.summary()
                if extracted:
                    return self._clean_markdown(extracted)
            except Exception:
                pass

        # Try MainContentExtractor as last resort
        if MAIN_CONTENT_EXTRACTOR_AVAILABLE:
            try:
                extracted = MainContentExtractor.extract(html, output_format="markdown")
                if extracted:
                    return self._clean_markdown(extracted)
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
        return self._clean_markdown(html)

    def parse_html(self, raw_html: str) -> str:
        """Parse and clean HTML content, extracting main content as markdown.

        Args:
            raw_html: Raw HTML content

        Returns:
            Cleaned markdown content extracted from HTML
        """
        if not raw_html:
            return ""

        return self._extract_markdown_from_html(raw_html)

    def parse_article(self, article: dict) -> dict:
        """Parse all fields of an article.

        Args:
            article: Dictionary containing raw article data

        Returns:
            Dictionary with parsed article data
        """
        return {
            "title": self.parse_title(article.get("title", "")),
            "url": self.parse_url(article.get("url", "")),
            "url_domain": self.parse_url_domain(article.get("url", "")),
            "published_date": self.parse_published_date(
                article.get("published_date", "")
            ),
            "summary": self.parse_summary(article.get("summary", "")),
            "tags": self.parse_tags(article.get("tags", "")),
            "html_content": self.parse_html(article.get("html_content", "")),
        }
