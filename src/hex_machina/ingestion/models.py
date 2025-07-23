"""Data models for Hex Machina v2 ingestion."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RssArticlePreview(BaseModel):
    """Represents a minimal article extracted from an RSS feed before enrichment."""

    title: str = Field(..., description="Article title")
    url: str = Field(..., description="URL of the article")
    published_date: datetime = Field(..., description="Publication date")
    author: Optional[str] = Field(None, description="Article author, if available")
    summary: Optional[str] = Field(
        None, description="Article summary or description, if available"
    )
    tags: Optional[list[str]] = Field(
        None, description="List of tags or categories, if available"
    )


class ArticleModel(RssArticlePreview):
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
