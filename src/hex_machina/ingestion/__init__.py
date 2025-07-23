"""Ingestion module for Hex Machina v2."""

from .article_parser import ArticleParser
from .models import ArticleModel
from .scrapers import (
    BaseArticleScraper,
    PlaywrightRSSArticleScraper,
    RSSArticleScraper,
    StealthPlaywrightRSSArticleScraper,
)
from .utils import (
    get_global_settings,
    get_rss_feeds_by_scraper,
    load_rss_feeds,
    load_scraping_config,
)

__all__ = [
    "ArticleModel",
    "ArticleParser",
    "BaseArticleScraper",
    "RSSArticleScraper",
    "PlaywrightRSSArticleScraper",
    "StealthPlaywrightRSSArticleScraper",
    "load_rss_feeds",
    "load_scraping_config",
    "get_global_settings",
    "get_rss_feeds_by_scraper",
]
