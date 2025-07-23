"""Hex Machina v2 - AI-driven newsletter service."""

from .ingestion import (
    ArticleModel,
    ArticleParser,
    BaseArticleScraper,
    PlaywrightRSSArticleScraper,
    RSSArticleScraper,
    StealthPlaywrightRSSArticleScraper,
)
from .utils import DateParser

__version__ = "0.1.0"
__author__ = "Mathieu Crilout"
__email__ = "mathieu.crilout@gmail.com"

__all__ = [
    "ArticleModel",
    "ArticleParser",
    "BaseArticleScraper",
    "RSSArticleScraper",
    "PlaywrightRSSArticleScraper",
    "StealthPlaywrightRSSArticleScraper",
    "DateParser",
]
