"""HTML article scraper for Hex Machina v2."""

from abc import abstractmethod
from datetime import datetime
from typing import Any, List, Optional

import scrapy
from parsel import Selector

from src.hex_machina.ingestion.article_models import ArticleModel
from src.hex_machina.ingestion.scrapers.base_article_scraper import BaseArticleScraper
from src.hex_machina.utils.date_parser import DateParser


class ScrapyHtmlArticleScraper(BaseArticleScraper):
    """Scrapy HTML scraper that handles HTML page parsing logic with pure Scrapy."""

    name = "scrapy_html_article_scraper"

    def __init__(
        self,
        scraper_config,
        start_urls: Optional[List[str]] = None,
        **kwargs,
    ):
        """Initialize the ScrapyHtmlArticleScraper.

        Args:
            scraper_config: The configuration object for this scraper (from parent).
            start_urls: List of URLs to start scraping from.
        """
        BaseArticleScraper.__init__(
            self, scraper_config=scraper_config, start_urls=start_urls, **kwargs
        )
        # Logger is inherited from BaseArticleScraper
        self.start_urls = start_urls

        # Configuration for HTML scraping
        self.max_articles_per_page = scraper_config.get("max_articles_per_page", 6)
        self.articles_limit = scraper_config.get("articles_limit")
        self.articles_parsed = 0

    @abstractmethod
    def extract_article_links(self, response) -> List[str]:
        """Extract article links from the HTML page.

        Args:
            response: Scrapy response object

        Returns:
            List of article URLs found on the page
        """
        pass

    @abstractmethod
    def load_more_articles(self, response) -> None:
        """Load more articles if needed (pagination, infinite scroll, etc.).

        Args:
            selector: Scrapy selector object
        """
        pass

    @abstractmethod
    def get_published_date(self, selector) -> Optional[str]:
        """
        Extract the published date from the article page.

        Args:
            selector: Scrapy selector object

        Returns:
            Published date string or None if not found
        """
        pass

    @abstractmethod
    def get_author(self, selector) -> Optional[str]:
        """
        Extract the author from the article page.

        Args:
            selector: Scrapy selector object

        Returns:
            Author string or None if not found
        """
        pass

    @abstractmethod
    def get_title(self, selector) -> Optional[str]:
        """
        Extract the title from the article page.

        Args:
            selector: Scrapy selector object

        Returns:
            Title string or None if not found
        """
        pass

    def limit_is_reached(self) -> bool:
        """Check if the article limit has been reached.

        Returns:
            True if limit is reached, False otherwise
        """
        if not self.articles_limit or self.articles_parsed < self.articles_limit:
            return False

        return True

    def _extract_article_fields(
        self, article: ArticleModel, html_content: str
    ) -> ArticleModel:
        """Extract article fields from HTML content.

        Args:
            article: Article model to populate
            html_content: HTML content to parse

        Returns:
            Populated ArticleModel
        """
        selector = Selector(text=html_content)

        # Extract title
        title = self.get_title(selector)
        if not title:
            article.ingestion_error_status = "title_not_found"
            article.ingestion_error_message = "Title not found"
            title = "fake_title_" + str(datetime.now())
        article.title = title

        # Extract published date
        published_date = self.get_published_date(selector)
        published_date = DateParser.parse_date(published_date)
        if not published_date:
            article.ingestion_error_status = "published_date_not_found"
            article.ingestion_error_message = "Published date not found"
            published_date = datetime.now()
        article.published_date = published_date

        # Extract text content
        text_content = self.get_text_content(html_content)
        if not text_content:
            article.ingestion_error_status = "text_content_not_found"
            article.ingestion_error_message = "Text content not found"
            text_content = ""
        article.text_content = text_content

        # Extract author
        author = self.get_author(selector)
        article.author = author

        article = ArticleModel.model_validate(article)
        return article

    async def parse_start_url(self, response, **kwargs):
        """Parse the response and extract article content from the start URL.

        Args:
            response: Scrapy response object
            **kwargs: Additional keyword arguments
        """
        page_url = response.meta.get("page_url", response.url)
        self._logger.info(f"Parsing HTML page: {page_url}")

        if response.status != 200:
            self._logger.warning(
                f"Failed to load page {response.url}: status {response.status}"
            )
            return

        # Load more articles if needed (pagination, infinite scroll, etc.)
        self.load_more_articles(response)

        # Extract article links from the page
        article_links = list(dict.fromkeys(self.extract_article_links(response)))
        article_links = article_links[: self.max_articles_per_page]

        if not article_links:
            self._logger.info(f"No article links found on {response.url}")
        else:
            self._logger.info(
                f"Found {len(article_links)} article links on {response.url}"
            )

            # Process each article link
            for link in article_links:
                if self.limit_is_reached():
                    break

                # Create Scrapy request
                request = scrapy.Request(
                    url=link,
                    callback=self.parse_article,
                    errback=self.handle_error,
                    headers=self.get_default_headers("article"),
                    meta={
                        "dont_cache": True,  # Don't cache article requests
                        "dont_retry": False,  # Allow retries
                    },
                    dont_filter=True,
                )

                yield request
                self.articles_parsed += 1
                self._logger.info(f"Scheduled article: {link}")

    async def parse_article(self, response: scrapy.http.Response) -> Any:
        """Parse individual article page content with Scrapy.

        Args:
            response: Scrapy response object

        Returns:
            ArticleModel with extracted content
        """
        # Log the response status for monitoring
        self._logger.info(
            f"Processing article from {response.url} with status code: {response.status}"
        )

        try:
            # Handle different HTTP status codes
            if response.status != 200:
                article = await self._handle_non_200_response(response)
                yield article
                return

            # Get HTML content from Scrapy response
            html_content = response.text

            # Create article model
            article = ArticleModel(
                source_url=self.start_urls[0],
                url=response.url,
                url_domain=self.parser.parse_url_domain(response.url),
                html_content=html_content,
                text_content="",
                published_date=datetime.now(),
                author="",
                title="",
                article_metadata={},
                ingestion_metadata={
                    "scraper_name": self.name,
                    "blocking_found": False,
                    "response_size": len(html_content),
                    "status_code": response.status,
                },
            )

            # Extract article fields
            article = self._extract_article_fields(article, html_content)
            if not self.check_published_date(article.published_date):
                self._logger.debug(
                    f"Skipping old article: '{article.title}' from {article.url}"
                )
                return

            self._logger.info(
                f"Successfully processed article: {article.title} (Size: {len(html_content)} chars)"
            )

        except Exception as e:
            self._logger.error(
                f"Error processing response content for {response.url}: {str(e)}"
            )
            article = ArticleModel(
                source_url=self.start_urls[0],
                url=response.url,
                url_domain=self.parser.parse_url_domain(response.url),
                html_content=response.text,
                text_content="",
                published_date=datetime.now(),
                author="",
                title="",
                article_metadata={},
                ingestion_metadata={
                    "scraper_name": self.name,
                    "error": str(e),
                    "status_code": response.status,
                },
            )
            article.ingestion_error_status = "response_processing_error"
            article.ingestion_error_message = str(e)

        yield article

    async def _handle_non_200_response(
        self, response: scrapy.http.Response
    ) -> ArticleModel:
        """
        Handle non-200 HTTP responses gracefully.

        Args:
            response: The Scrapy response object

        Returns:
            ArticleModel with error information
        """
        status_code = response.status
        html_content = response.text

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
            error_status = "access_denied"
        elif status_code == 404:
            error_status = "not_found"
        elif status_code in [500, 502, 503, 504]:
            error_status = "server_error"
        else:
            error_status = f"http_error_{status_code}"

        # Create article with error information
        article = ArticleModel(
            source_url=self.start_urls[0],
            url=response.url,
            url_domain=self.parser.parse_url_domain(response.url),
            html_content=html_content,
            text_content=self.get_text_content(html_content),
            published_date=datetime.now(),
            author="",
            title="",
            article_metadata={},
            ingestion_metadata={
                "scraper_name": self.name,
                "status_code": status_code,
                "response_size": len(html_content),
                "error_type": "http_error",
            },
        )

        article.ingestion_error_status = error_status
        article.ingestion_error_message = error_message

        # Log the error with context
        self._logger.warning(
            f"HTTP {status_code} for article {response.url}: {error_message}"
        )

        return article

    async def handle_error(self, failure: Any) -> Any:
        """
        Handle request errors and extract error information for Scrapy-based scrapers.

        Args:
            failure: Scrapy failure object

        Returns:
            List containing the updated article if present, otherwise empty list.
        """
        request = failure.request

        error_info = {
            "url": request.url,
            "error_type": str(failure.type),
            "error_message": str(failure.value),
        }

        # Handle specific error types
        if "DNSLookupError" in error_info["error_type"]:
            self._logger.warning(
                f"DNS lookup failed for {error_info['url']}: {error_info['error_message']}"
            )
        elif "TimeoutError" in error_info["error_type"]:
            self._logger.warning(
                f"Request timeout for {error_info['url']}: {error_info['error_message']}"
            )
        elif "HttpError" in error_info["error_type"]:
            self._logger.warning(
                f"HTTP error for {error_info['url']}: {error_info['error_message']}"
            )
        else:
            self._logger.error(
                f"Error processing article {error_info['url']}: {error_info['error_message']}"
            )

        # Create article with error information
        article = ArticleModel(
            source_url=self.start_urls[0],
            url=request.url,
            url_domain=self.parser.parse_url_domain(request.url),
            html_content="",
            text_content="",
            published_date=datetime.now(),
            author="",
            title="",
            article_metadata={},
            ingestion_metadata={
                "scraper_name": self.name,
                "error": error_info,
            },
        )

        article.ingestion_error_status = str(failure.type)
        article.ingestion_error_message = error_info["error_message"]

        return [article]

    def get_default_headers(self, content_type: str = "article") -> dict:
        """
        Get default headers for different content types.

        Args:
            content_type: Type of content being requested ("rss", "html", "article")

        Returns:
            Dictionary of headers appropriate for the content type
        """
        base_headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",  # No Brotli to avoid dependency issues
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
            "Connection": "keep-alive",
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
