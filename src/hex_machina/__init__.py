"""Hex Machina v2 - AI-driven newsletter service."""

from .ingestion import (
    ArticleParser,
    BaseArticleScraper,
    PlaywrightRSSArticleScraper,
    RSSArticleScraper,
    ScrapedArticle,
    StealthPlaywrightRSSArticleScraper,
)
from .utils import DateParser

__version__ = "0.1.0"
__author__ = "Mathieu Crilout"
__email__ = "mathieu.crilout@gmail.com"

__all__ = [
    "ScrapedArticle",
    "ArticleParser",
    "BaseArticleScraper",
    "RSSArticleScraper",
    "PlaywrightRSSArticleScraper",
    "StealthPlaywrightRSSArticleScraper",
    "DateParser",
]
