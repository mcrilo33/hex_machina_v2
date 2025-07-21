"""Data models for Hex Machina v2 ingestion."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ScrapedArticle(BaseModel):
    """Represents an article scraped from a source."""

    title: str = Field(..., description="Article title")
    url: str = Field(..., description="URL of the article")
    source_url: str = Field(..., description="URL of the RSS feed source")
    url_domain: str = Field(..., description="Domain of the article URL")
    published_date: datetime = Field(..., description="Publication date")
    html_content: str = Field(..., description="Raw HTML content")
    text_content: str = Field(..., description="Extracted text content")
    author: Optional[str] = Field(None, description="Article author")
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
