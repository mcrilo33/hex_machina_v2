"""Data models for Hex Machina v2 ingestion."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from src.hex_machina.ingestion.article_parser import ArticleParser
from src.hex_machina.utils.date_parser import DateParser

PARSER = ArticleParser()


class RSSArticlePreview(BaseModel):
    """Represents a minimal article extracted from an RSS feed before enrichment."""

    title: str = Field(..., description="Article title")
    url: str = Field(..., description="URL of the article")
    published_date: datetime = Field(..., description="Publication date")
    author: Optional[str] = Field(None, description="Article author, if available")
    summary: Optional[str] = Field(
        None, description="Article summary or description, if available"
    )
    tags: Optional[List[str]] = Field(
        None, description="List of tags or categories, if available"
    )
    url_domain: Optional[str] = Field(None, description="Domain of the article URL")

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, v):
        return PARSER.parse_title(v)

    @field_validator("url", mode="before")
    @classmethod
    def clean_url(cls, v):
        return PARSER.parse_url(v)

    @field_validator("author", mode="before")
    @classmethod
    def clean_author(cls, v):
        return PARSER.parse_author(v)

    @field_validator("summary", mode="before")
    @classmethod
    def clean_summary(cls, v):
        return PARSER.parse_summary(v)

    @field_validator("tags", mode="before")
    @classmethod
    def clean_tags(cls, v):
        return PARSER.parse_tags(v)

    @field_validator("published_date", mode="before")
    @classmethod
    def parse_published_date(cls, v):
        if isinstance(v, datetime):
            return v
        return DateParser.parse_date(v)

    @field_validator("url_domain", mode="after")
    @classmethod
    def set_url_domain(cls, v, values):
        url = values.data.get("url")
        return PARSER.parse_url_domain(url) if url else v

    @classmethod
    def from_feed_entry(cls, entry: dict, extract_domain=None) -> "RSSArticlePreview":
        """Create a RSSArticlePreview from a feedparser entry dict.

        Args:
            entry: The feedparser entry dict.
            extract_domain: Optional function to extract domain from a URL.
        Returns:
            RSSArticlePreview instance.
        """
        if extract_domain is None:
            from urllib.parse import urlparse

            def extract_domain(url):
                return urlparse(url).netloc if url else None

        return cls(
            title=entry.get("title"),
            author=entry.get("author", entry.get("dc_creator", "")),
            published_date=entry.get("published", entry.get("updated", "")),
            url=entry.get("link", entry.get("url")),
            url_domain=extract_domain(entry.get("link")),
            summary=entry.get("summary", entry.get("description", "")),
            tags=(
                [tag["term"] for tag in entry.get("tags", [])]
                if "tags" in entry
                else []
            ),
        )


class ArticleModel(RSSArticlePreview):
    """Represents a fully enriched article scraped from a source (Pydantic model)."""

    source_url: str = Field(..., description="URL of the RSS feed source")
    url_domain: str = Field(..., description="Domain of the article URL")
    html_content: str = Field(..., description="Raw HTML content")
    text_content: str = Field(..., description="Extracted text content")
    article_metadata: dict = Field(
        default_factory=dict, description="Article metadata (tags, summary, etc.)"
    )
    ingestion_metadata: Optional[dict] = Field(
        default_factory=dict,
        description="Ingestion-related metadata (e.g., scraper name, source, errors, etc.)",
    )
    ingestion_error_status: Optional[str] = Field(
        None, description="Ingestion error status if ingestion failed"
    )
    ingestion_error_message: Optional[str] = Field(
        None, description="Ingestion error message if ingestion failed"
    )
