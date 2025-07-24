"""Base article scraper for Hex Machina v2."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

import scrapy

from src.hex_machina.ingestion.article_parser import ArticleParser
from src.hex_machina.utils import DateParser
from src.hex_machina.utils.logging_utils import get_logger


class BaseArticleScraper(scrapy.Spider, ABC):
    """Abstract base class for all article scrapers in Hex Machina v2."""

    name: str = "base_article_scraper"

    def __init__(
        self,
        scraper_config,
        start_urls: Optional[List[str]] = None,
        **kwargs,
    ):
        """Initialize the base scraper.

        Args:
            scraper_config: The configuration object for this scraper (e.g., ScraperConfig).
            start_urls: List of URLs to start scraping from.
        """
        super().__init__(**kwargs)
        self.scraper_config = scraper_config
        self._logger = get_logger(f"hex_machina.scraper.{self.name}")
        self.start_urls = start_urls or []
        self.parser = ArticleParser()

    async def start(self):
        """Start requests for RSS feeds using Scrapy's entry point.

        Yields:
            Scrapy Request objects for each start URL.
        """
        # Read settings when spider starts
        self._load_settings_from_scrapy()

        self._logger.info(
            f"Starting {self.name} scraper with {len(self.start_urls)} feeds"
        )
        self._logger.info(
            f"Date threshold: {self.limit_date.isoformat() if self.limit_date else 'None'}"
        )
        if self.articles_limit:
            self._logger.info(f"Articles limit: {self.articles_limit}")

        for start_url in self.start_urls:
            self._logger.debug(f"Yielding request for RSS feed: {start_url}")
            yield scrapy.Request(
                url=start_url,
                callback=self.parse_start_url,
                errback=self.handle_error,
                meta={"feed_url": start_url},
            )

    def _load_settings_from_scrapy(self):
        """Load configuration from Scrapy settings."""
        # Get date threshold from settings
        date_threshold_str = self.settings.get("INGESTION_DATE_THRESHOLD")
        if date_threshold_str:
            try:
                self.limit_date = DateParser.parse_date(date_threshold_str)
                self._logger.info(
                    f"Loaded date threshold from settings: {self.limit_date}"
                )
            except Exception as e:
                self._logger.warning(
                    f"Failed to parse date threshold '{date_threshold_str}': {e}"
                )

        # Get articles limit from settings
        self.articles_limit = self.settings.get("CLOSESPIDER_ITEMCOUNT")
        if self.articles_limit:
            self._logger.info(
                f"Loaded articles limit from settings: {self.articles_limit}"
            )

    def _log_scraping_summary(self, articles: List) -> None:
        """Log a summary of the scraping results.

        Args:
            articles: List of scraped articles
        """
        if not articles:
            self._logger.warning("No articles were scraped")
            return

        # Group articles by domain
        domains = {}
        for article in articles:
            domain = getattr(article, "url_domain", None)
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(article)

        # Log summary by domain
        self._logger.info("Scraping summary by domain:")
        for domain, domain_articles in domains.items():
            self._logger.info(f"  {domain}: {len(domain_articles)} articles")

        # Log article details in debug mode
        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug("Detailed article list:")
            for i, article in enumerate(articles, 1):
                self._logger.debug(
                    f"  {i}. '{getattr(article, 'title', '')}' - {getattr(article, 'url', '')} "
                    f"({getattr(article, 'published_date', 'No date')})"
                )

    @abstractmethod
    async def parse_start_url(self, response, **kwargs):
        """Parse the response and extract article content from the start/feed URL.

        Args:
            response: Scrapy response object
            **kwargs: Additional keyword arguments
        """
        pass

    @abstractmethod
    async def parse_article(self, response, **kwargs):
        """Parse individual article content.

        Args:
            response: Scrapy response object
            **kwargs: Additional keyword arguments
        """
        pass

    def check_published_date(self, published_date: datetime) -> bool:
        """Check if article is recent enough.

        Args:
            published_date: Article publication date

        Returns:
            True if article is recent enough, False otherwise
        """
        is_recent = DateParser.is_date_after_threshold(published_date, self.limit_date)
        if not is_recent and published_date and self.limit_date:
            self._logger.debug(
                f"Article too old: {published_date.isoformat()} < {self.limit_date.isoformat()}"
            )
        return is_recent

    async def handle_error(self, failure):
        """Handle request errors.

        Args:
            failure: Scrapy failure object
        """
        self._logger.error(f"Request failed: {getattr(failure, 'value', failure)}")
        # Subclasses should yield or return error info as needed

    def parse_html(self, html_content: str) -> tuple[str, Optional[str], Optional[str]]:
        """Parse HTML content to extract text, with error handling.

        Args:
            html_content: The HTML content to parse.

        Returns:
            tuple: (text_content, error_status, error_message)
        """
        error_status = None
        error_message = None
        text_content = ""
        try:
            text_content = self.parser.parse_html(html_content)
        except Exception as e:
            self._logger.warning(f"Error extracting article text: {e}")
            error_status = "extract_error"
            error_message = str(e)
        return text_content, error_status, error_message
