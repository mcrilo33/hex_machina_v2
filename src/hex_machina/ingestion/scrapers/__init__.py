"""Scrapers module for Hex Machina v2."""

from src.hex_machina.ingestion.scrapers.base_article_scraper import BaseArticleScraper
from src.hex_machina.ingestion.scrapers.html_article_scrapers.deepmind_google_scraper import (
    DeepMindGoogleScraper,
)
from src.hex_machina.ingestion.scrapers.html_article_scrapers.hai_scraper import (
    HAIScraper,
)
from src.hex_machina.ingestion.scrapers.html_article_scrapers.hbr_scraper import (
    HBRScraper,
)
from src.hex_machina.ingestion.scrapers.html_article_scrapers.meta_scraper import (
    MetaScraper,
)
from src.hex_machina.ingestion.scrapers.html_article_scrapers.microsoft_scraper import (
    MicrosoftScraper,
)
from src.hex_machina.ingestion.scrapers.html_article_scrapers.research_google_scraper import (
    ResearchGoogleScraper,
)
from src.hex_machina.ingestion.scrapers.html_article_scrapers.synced_review_scraper import (
    SyncedReviewScraper,
)
from src.hex_machina.ingestion.scrapers.playwright_rss_article_scraper import (
    PlaywrightRSSArticleScraper,
)
from src.hex_machina.ingestion.scrapers.rss_article_scraper import RSSArticleScraper
from src.hex_machina.ingestion.scrapers.scrapy_rss_article_scraper import (
    ScrapyRSSArticleScraper,
)
from src.hex_machina.ingestion.scrapers.simple_playwright_rss_article_scraper import (
    SimplePlaywrightRSSArticleScraper,
)
from src.hex_machina.ingestion.scrapers.standalone_playwright_rss_article_scraper import (
    StandalonePlaywrightRSSArticleScraper,
)
from src.hex_machina.ingestion.scrapers.stealth_playwright_rss_article_scraper import (
    StealthPlaywrightRSSArticleScraper,
)

__all__ = [
    "BaseArticleScraper",
    "DeepMindGoogleScraper",
    "HAIScraper",
    "HBRScraper",
    "MetaScraper",
    "MicrosoftScraper",
    "RSSArticleScraper",
    "PlaywrightRSSArticleScraper",
    "ResearchGoogleScraper",
    "ScrapyRSSArticleScraper",
    "SimplePlaywrightRSSArticleScraper",
    "SyncedReviewScraper",
    "StealthPlaywrightRSSArticleScraper",
    "StandalonePlaywrightRSSArticleScraper",
]
