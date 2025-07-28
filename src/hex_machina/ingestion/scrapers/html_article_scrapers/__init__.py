"""HTML article scrapers package for Hex Machina v2."""

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

__all__ = [
    "DeepMindGoogleScraper",
    "HAIScraper",
    "HBRScraper",
    "MetaScraper",
    "MicrosoftScraper",
    "ResearchGoogleScraper",
    "SyncedReviewScraper",
]
