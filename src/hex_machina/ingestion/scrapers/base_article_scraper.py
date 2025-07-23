"""Base article scraper for Hex Machina v2."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

import scrapy

from ...utils import DateParser
from ..article_parser import ArticleParser


class BaseArticleScraper(scrapy.Spider, ABC):
    """Abstract base class for article scrapers.

    Note:
        All storage and existence checking is handled by the Scrapy Item Pipeline (ArticleStorePipeline).
        This class should only yield Article items and increment processed_counter accordingly.
    """

    name = "base_article_scraper"  # Default name, should be overridden by subclasses

    def __init__(
        self,
        processed_limit: int = 100,
        limit_date: Optional[datetime] = None,
        start_urls: Optional[List[str]] = None,
    ) -> None:
        """Initialize the scraper.

        Args:
            processed_limit: Maximum number of articles to process
            limit_date: Minimum date for articles (articles older than this will be skipped)
            start_urls: List of URLs to start scraping from
        """
        super().__init__()
        # self._logger = logging.getLogger(f"hex_machina.scraper.{self.name}")
        self.processed_counter = 0
        self.processed_limit = processed_limit or None
        self.limit_date = limit_date
        self.start_urls = start_urls or []
        self.parser = ArticleParser()

    def check_published_date(self, published_date: datetime) -> bool:
        """Check if article is recent enough.

        Args:
            published_date: Article publication date

        Returns:
            True if article is recent enough, False otherwise
        """
        # Use DateParser for timezone-aware comparison
        is_recent = DateParser.is_date_after_threshold(published_date, self.limit_date)

        if not is_recent and published_date and self.limit_date:
            self.logger.debug(
                f"Article too old: {published_date.isoformat()} < {self.limit_date.isoformat()}"
            )
        return is_recent

    def handle_error(self, failure):
        """Handle request errors.

        Args:
            failure: Scrapy failure object
        """
        self.logger.error(f"Request failed: {failure.value}")

    async def start(self):
        """Start requests for RSS feeds using Scrapy's async entry point (Scrapy 2.13+)."""
        self.logger.info(
            f"Starting {self.name} scraper with {len(self.start_urls)} feeds"
        )
        self.logger.info(f"Article limit: {self.processed_limit}")
        self.logger.info(f"Date threshold: {self.limit_date.isoformat()}")
        for start_url in self.start_urls:
            self.logger.debug(f"Yielding request for RSS feed: {start_url}")
            yield scrapy.Request(
                url=start_url,
                callback=self.parse_start_url,
                errback=self.handle_error,
                meta={"feed_url": start_url},
            )

    def _log_scraping_summary(self, articles) -> None:
        """Log a summary of the scraping results.

        Args:
            articles: List of scraped articles
        """
        if not articles:
            self.logger.warning("No articles were scraped")
            return

        # Group articles by domain
        domains = {}
        for article in articles:
            domain = article.url_domain
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(article)

        # Log summary by domain
        self.logger.info("Scraping summary by domain:")
        for domain, domain_articles in domains.items():
            self.logger.info(f"  {domain}: {len(domain_articles)} articles")

        # Log article details in debug mode
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("Detailed article list:")
            for i, article in enumerate(articles, 1):
                self.logger.debug(
                    f"  {i}. '{article.title}' - {article.url} "
                    f"({article.published_date.isoformat() if article.published_date else 'No date'})"
                )

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
            self.logger.warning(f"Error extracting article text: {e}")
            error_status = "extract_error"
            error_message = str(e)
        return text_content, error_status, error_message

    @abstractmethod
    def parse_start_url(self, response, **kwargs):
        """Parse the response and extract article content from the start/feed URL.

        Args:
            response: Scrapy response object
            **kwargs: Additional keyword arguments
        Note:
            Subclasses should increment self.processed_counter each time an Article is yielded.
        """
        pass

    @abstractmethod
    def parse_article(self, response, **kwargs):
        """Parse the response for an individual article page.

        Args:
            response: Scrapy response object
            **kwargs: Additional keyword arguments
        Returns:
            Should yield an Article or dict matching Article fields.
        """
        pass
