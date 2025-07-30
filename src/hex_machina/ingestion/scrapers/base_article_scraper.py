"""Base article scraper for Hex Machina v2."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

import scrapy

from src.hex_machina.ingestion.article_parser import ArticleParser
from src.hex_machina.utils import DateParser, extract_markdown_from_html


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
        # All scrapers inherit this logger
        self._logger = logging.getLogger(f"hex_machina.scraper.{self.name}")
        self.start_urls = start_urls or []
        self.parser = ArticleParser()

        # Load date threshold from scraper config
        self.date_threshold = None
        if scraper_config.get("date_threshold"):
            try:
                self.date_threshold = DateParser.parse_date(
                    scraper_config["date_threshold"]
                )
                self._logger.info(
                    f"Loaded date threshold from config: {self.date_threshold}"
                )
            except Exception as e:
                self._logger.warning(
                    f"Failed to parse date threshold '{scraper_config['date_threshold']}': {e}"
                )

        # Load articles limit from scraper config
        self.articles_limit = scraper_config.get("articles_limit")
        if self.articles_limit:
            self._logger.info(
                f"Loaded articles limit from config: {self.articles_limit}"
            )

    async def start(self):
        """Start requests for RSS feeds using Scrapy's entry point.

        Yields:
            Scrapy Request objects for each start URL.
        """
        self._logger.info(
            f"Starting {self.name} scraper with {len(self.start_urls)} feeds"
        )
        self._logger.info(
            f"Date threshold: {self.date_threshold.isoformat() if self.date_threshold else 'None'}"
        )
        if self.articles_limit:
            self._logger.info(f"Articles limit: {self.articles_limit}")

        for start_url in self.start_urls:
            self._logger.debug(f"Yielding request for RSS feed: {start_url}")
            yield scrapy.Request(
                url=start_url,
                callback=self.parse_start_url,
                errback=self.handle_error,
                headers=self.get_default_headers("rss"),
                meta={
                    "feed_url": start_url,
                },
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
        """Check if article is too old compared to the date threshold.

        Args:
            published_date: Article publication date

        Returns:
            True if article is recent enough, False if too old
        """
        if not self.date_threshold:
            # No date threshold set, accept all articles
            return True

        if not published_date:
            # No published date available, skip article
            return False

        # Handle timezone-aware vs timezone-naive datetime comparison
        from datetime import timezone

        threshold = self.date_threshold
        if threshold.tzinfo is None and published_date.tzinfo is not None:
            # Make threshold timezone-aware by assuming UTC
            threshold = threshold.replace(tzinfo=timezone.utc)
        elif threshold.tzinfo is not None and published_date.tzinfo is None:
            # Make published_date timezone-aware by assuming UTC
            published_date = published_date.replace(tzinfo=timezone.utc)

        is_too_old = published_date < threshold
        if is_too_old:
            self._logger.debug(
                f"Article too old: {published_date.isoformat()} < {threshold.isoformat()}"
            )
        return not is_too_old

    async def handle_error(self, failure):
        """Handle request errors.

        Args:
            failure: Scrapy failure object
        """
        request = failure.request
        error_type = getattr(failure, "type", "Unknown")
        error_value = getattr(failure, "value", failure)

        # Extract more detailed error information
        if hasattr(error_value, "response"):
            status_code = error_value.response.status
            url = error_value.response.url
            self._logger.error(
                f"Request failed for {url}: HTTP {status_code} - {error_type}: {error_value}"
            )

            # Log specific error types for better debugging
            if status_code == 520:
                self._logger.warning(
                    f"Cloudflare 520 error detected for {url}. This usually indicates "
                    f"the origin server is unreachable. Consider retrying later or "
                    f"checking if the site is experiencing issues."
                )
            elif status_code in [521, 522, 523, 524]:
                self._logger.warning(
                    f"Cloudflare error {status_code} detected for {url}. "
                    f"This indicates server connectivity issues."
                )
            elif status_code == 429:
                self._logger.warning(
                    f"Rate limit (429) detected for {url}. Consider increasing delays."
                )
        else:
            self._logger.error(
                f"Request failed for {request.url}: {error_type}: {error_value}"
            )

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

    def get_text_content(self, html_content: str) -> Optional[str]:
        """
        Extract the main text content from the article page.
        Gets all text content within the section.

        Args:
            response: Scrapy response object

        Returns:
            Extracted text content as a string, or None if not found
        """
        content_elements = extract_markdown_from_html(html_content)
        return content_elements

    def get_default_headers(self, content_type: str = "rss") -> dict:
        """
        Get default headers for different content types.

        Args:
            content_type: Type of content being requested ("rss", "html", "article")

        Returns:
            Dictionary of headers appropriate for the content type
        """
        base_headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
        }

        if content_type == "rss":
            base_headers["Accept"] = (
                "application/rss+xml, application/xml, text/xml, */*"
            )
        elif content_type == "html":
            base_headers["Accept"] = (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            )
        elif content_type == "article":
            base_headers["Accept"] = (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            )
        else:
            base_headers["Accept"] = "*/*"

        return base_headers
