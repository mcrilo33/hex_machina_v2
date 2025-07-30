"""Simple Playwright RSS article scraper for Hex Machina v2."""

from typing import Any, Optional

import scrapy

from src.hex_machina.ingestion.article_models import ArticleModel
from src.hex_machina.ingestion.scrapers.playwright_mixin import PlaywrightMixin
from src.hex_machina.ingestion.scrapers.rss_article_scraper import RSSArticleScraper


class SimplePlaywrightRSSArticleScraper(RSSArticleScraper, PlaywrightMixin):
    """Simple scraper for articles using Playwright for JavaScript rendering."""

    name = "simple_playwright_rss_article_scraper"

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
        PlaywrightMixin.__init__(self)

    async def parse_article(self, article: ArticleModel) -> Any:
        """Schedule a Playwright request to parse the article content.

        Uses Playwright for JavaScript rendering with simple, common features.
        """
        # Create Playwright request using the mixin
        request = await self.create_playwright_request(
            url=article.url,
            callback=self.parse,
            errback=self.handle_playwright_error,
            article=article,
            use_advanced_stealth=False,  # Use simple stealth
        )

        yield request

    async def parse(self, response: scrapy.http.Response) -> Any:
        """Parse the article content with JavaScript rendering."""

        article = response.meta.get("scraped_article")
        if not article:
            self._logger.error("No article found in response meta")
            return

        # Log the response status for monitoring
        self._logger.info(
            f"Processing article '{article.title}' with status code: {response.status}"
        )

        try:
            # Get HTML content from Playwright page
            page = response.meta.get("playwright_page")
            if page:
                try:
                    # Wait for common content to load
                    await page.wait_for_load_state("networkidle", timeout=10000)

                    # Get the full HTML content after JavaScript execution
                    html_content = await page.content()

                    # Extract text content
                    text_content = await page.evaluate("() => document.body.innerText")

                    # Handle different HTTP status codes
                    if response.status != 200:
                        await self._handle_non_200_response(
                            article, response, html_content, text_content
                        )
                        yield article
                        return

                    article.html_content = html_content
                    article.text_content = text_content
                    article.ingestion_metadata = {
                        "scraper_name": self.name,
                        "status_code": response.status,
                        "response_size": len(html_content),
                        "fake_content_detection": fake_content_result,
                    }

                    self._logger.info(
                        f"Successfully processed article: {article.title} "
                        f"(Size: {len(html_content)} chars, Quality: {fake_content_result['content_quality_score']:.2f})"
                    )

                except Exception as e:
                    self._logger.error(
                        f"Error processing page content for {article.title}: {str(e)}"
                    )
                    article.ingestion_error_status = "page_processing_error"
                    article.ingestion_error_message = str(e)
                    article.ingestion_metadata = {
                        "scraper_name": self.name,
                        "error": str(e),
                    }
                finally:
                    await page.close()
            else:
                self._logger.warning(
                    f"Playwright page not available for {response.url}. Using fallback HTML content."
                )
                html_content = response.text
                text_content = self.get_text_content(html_content)

                # Handle fallback content
                await self._handle_fallback_content(
                    article, response, html_content, text_content
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
        self,
        article: ArticleModel,
        response: scrapy.http.Response,
        html_content: str,
        text_content: str,
    ) -> None:
        """
        Handle non-200 HTTP responses gracefully.

        Args:
            article: The article being processed
            response: The Scrapy response object
            html_content: The HTML content from the response
            text_content: The text content from the response
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

        # Still store the content for debugging purposes
        article.html_content = html_content
        article.text_content = text_content

    async def handle_playwright_error(self, failure: Any) -> Any:
        """
        Handle Playwright-specific errors and extract error information.

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

        # Handle specific Playwright error types
        if "TimeoutError" in error_info["error_type"]:
            self._logger.warning(
                f"Playwright timeout for {error_info['article_title']}: {error_info['error_message']}"
            )
        elif "TargetClosedError" in error_info["error_type"]:
            self._logger.warning(
                f"Playwright target closed for {error_info['article_title']}: {error_info['error_message']}"
            )
        elif "NavigationError" in error_info["error_type"]:
            self._logger.warning(
                f"Playwright navigation error for {error_info['article_title']}: {error_info['error_message']}"
            )
        else:
            self._logger.error(
                f"Playwright error processing article {error_info['article_title']}: {error_info['error_message']}"
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
