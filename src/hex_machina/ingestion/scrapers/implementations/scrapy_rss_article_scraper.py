"""Scrapy RSS article scraper for Hex Machina v2."""

from typing import Any, Optional

import scrapy

from src.hex_machina.ingestion.models.article_models import ArticleModel
from src.hex_machina.ingestion.scrapers.base.rss_article_scraper import (
    RSSArticleScraper,
)


class ScrapyRSSArticleScraper(RSSArticleScraper):
    """Scraper for articles using pure Scrapy without Playwright."""

    name = "scrapy_rss_article_scraper"

    def __init__(
        self,
        scraper_config: dict,
        start_urls: Optional[list] = None,
        **kwargs,
    ) -> None:
        RSSArticleScraper.__init__(
            self,
            scraper_config=scraper_config,
            start_urls=start_urls,
            **kwargs,
        )

    async def parse_article(self, article: ArticleModel) -> Any:
        """Schedule a Scrapy request to parse the article content.

        Uses standard Scrapy requests without Playwright for better stability
        and faster processing for sites that don't require JavaScript rendering.
        """
        # Get domain-specific headers
        headers = self.get_default_headers("article", article.url_domain)

        # Create standard Scrapy request
        request = scrapy.Request(
            url=article.url,
            callback=self.parse,
            errback=self.handle_error,
            headers=headers,
            meta={
                "scraped_article": article,
                "dont_retry": False,  # Allow retries
            },
            dont_filter=True,
            cookies={},  # Disable cookies
        )

        yield request

    async def parse(self, response: scrapy.http.Response) -> Any:
        """Parse the article content and validate it."""

        article = response.meta.get("scraped_article")
        if not article:
            self._logger.error("No article found in response meta")
            return

        # Log the response status for monitoring
        self._logger.info(
            f"Processing article '{article.title}' with status code: {response.status}"
        )

        try:
            # Get HTML content from Scrapy response
            html_content = response.text

            # Handle different HTTP status codes
            if response.status != 200:
                await self._handle_non_200_response(article, response, html_content)
                yield article
                return

            article.html_content = html_content
            article.text_content = self.get_text_content(html_content)
            article.ingestion_metadata = {
                "scraper_name": self.name,
                "blocking_found": False,
                "response_size": len(html_content),
                "status_code": response.status,
            }

            self._logger.info(
                f"Successfully processed article: {article.title} (Size: {len(html_content)} chars)"
            )

        except Exception as e:
            self._logger.error(
                f"Error processing response content for {article.title}: {str(e)}"
            )
            article.ingestion_error_status = "response_processing_error"
            article.ingestion_error_message = str(e)
            article.ingestion_metadata = {
                "scraper_name": self.name,
                "error": str(e),
                "status_code": response.status,
            }

        yield article

    async def _handle_non_200_response(
        self, article: ArticleModel, response: scrapy.http.Response, html_content: str
    ) -> None:
        """
        Handle non-200 HTTP responses gracefully.

        Args:
            article: The article being processed
            response: The Scrapy response object
            html_content: The HTML content from the response
        """
        status_code = response.status

        # Map status codes to meaningful error messages
        status_messages = {
            403: "Forbidden - Access denied by server",
            404: "Not Found - Article URL is broken or expired",
            429: "Too Many Requests - Rate limited by server",
            500: "Internal Server Error - Server-side issue",
            502: "Bad Gateway - Server communication error",
            503: "Service Unavailable - Server temporarily unavailable",
            504: "Gateway Timeout - Server timeout",
        }

        error_message = status_messages.get(
            status_code, f"HTTP {status_code} - Unknown error"
        )

        # Set appropriate error status based on status code
        if status_code in [403, 429]:
            article.ingestion_error_status = "access_denied"
        elif status_code == 404:
            article.ingestion_error_status = "not_found"
        elif status_code in [500, 502, 503, 504]:
            article.ingestion_error_status = "server_error"
        else:
            article.ingestion_error_status = f"http_error_{status_code}"

        article.ingestion_error_message = error_message
        article.ingestion_metadata = {
            "scraper_name": self.name,
            "status_code": status_code,
            "response_size": len(html_content),
            "error_type": "http_error",
        }

        # Log the error with context
        self._logger.warning(
            f"HTTP {status_code} for article '{article.title}': {error_message}"
        )

        # Still store the HTML content for debugging purposes
        article.html_content = html_content
        article.text_content = self.get_text_content(html_content)

    async def handle_error(self, failure: Any) -> Any:
        """
        Handle request errors and extract error information for Scrapy-based scrapers.

        Args:
            failure: Scrapy failure object

        Returns:
            List containing the updated article if present, otherwise empty list.
        """
        request = failure.request
        article = request.meta.get("scraped_article")

        error_info = {
            "url": request.url,
            "error_type": str(failure.type),
            "error_message": str(failure.value),
            "article_title": getattr(article, "title", "Unknown"),
        }

        # Handle specific error types
        if "DNSLookupError" in error_info["error_type"]:
            self._logger.warning(
                f"DNS lookup failed for {error_info['article_title']}: {error_info['error_message']}"
            )
        elif "TimeoutError" in error_info["error_type"]:
            self._logger.warning(
                f"Request timeout for {error_info['article_title']}: {error_info['error_message']}"
            )
        elif "HttpError" in error_info["error_type"]:
            self._logger.warning(
                f"HTTP error for {error_info['article_title']}: {error_info['error_message']}"
            )
        else:
            self._logger.error(
                f"Error processing article {error_info['article_title']}: {error_info['error_message']}"
            )

        # Update article with error information
        if article:
            article.ingestion_error_status = str(failure.type)
            article.ingestion_error_message = error_info["error_message"]
            article.ingestion_metadata = {
                "scraper_name": self.name,
                "error": error_info,
            }
            return [article]
        return []

    def get_default_headers(
        self, content_type: str = "article", domain: str = None
    ) -> dict:
        """
        Get default headers for different content types and domains.

        Args:
            content_type: Type of content being requested ("rss", "html", "article")
            domain: Domain name to get specific headers for

        Returns:
            Dictionary of headers appropriate for the content type and domain
        """
        # Get domain headers configuration from settings
        domain_headers_config = self.settings.get("DOMAIN_HEADERS_CONFIG", {})

        # Start with default headers
        base_headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",  # No Brotli to avoid dependency issues
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "DNT": "1",
            "Connection": "keep-alive",
        }

        # Apply domain-specific headers if available
        if domain and domain in domain_headers_config:
            domain_config = domain_headers_config[domain]
            # Override base headers with domain-specific ones
            for header_name, header_value in domain_config.items():
                # Convert snake_case to Title-Case for header names
                header_key = "-".join(
                    word.capitalize() for word in header_name.split("_")
                )
                base_headers[header_key] = header_value
            self._logger.debug(f"Applied domain-specific headers for {domain}")
        elif domain:
            self._logger.debug(
                f"No domain-specific headers found for {domain}, using defaults"
            )

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
