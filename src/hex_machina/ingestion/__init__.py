"""Ingestion module for Hex Machina project."""

from .core import *
from .evaluation import *
from .models import *
from .processing import *
from .scrapers.base import *
from .scrapers.implementations import *

__all__ = [
    # Models
    "ArticleModel",
    "RSSArticlePreview",
    "IngestionConfig",
    # Core
    "IngestionRunner",
    "ConfigLoader",
    # Processing
    "ArticleParser",
    "ScrapyPipelines",
    # Evaluation
    "IngestionReportGenerator",
    "IngestionEvaluationReportGenerator",
    "IngestionDomainEvaluationReportGenerator",
    # Base Scrapers
    "BaseArticleScraper",
    "RSSArticleScraper",
    "PlaywrightMixin",
    "ScrapyHtmlArticleScraper",
    # Scraper Implementations
    "ScrapyRSSArticleScraper",
    "PlaywrightRSSArticleScraper",
    "StealthPlaywrightRSSArticleScraper",
    "SimplePlaywrightRSSArticleScraper",
    "StandalonePlaywrightRSSArticleScraper",
    # HTML Article Scrapers
    "DeepMindGoogleScraper",
    "HAIScraper",
    "HBRScraper",
    "MetaScraper",
    "MicrosoftScraper",
    "ResearchGoogleScraper",
    "SyncedReviewScraper",
]
