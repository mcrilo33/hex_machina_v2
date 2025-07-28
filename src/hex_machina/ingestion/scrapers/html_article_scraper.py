"""Playwright HTML article scraper for Hex Machina v2."""

from abc import abstractmethod
from datetime import datetime
from typing import List, Optional

from parsel import Selector

from src.hex_machina.ingestion.article_models import ArticleModel
from src.hex_machina.ingestion.content_validator import create_content_validator
from src.hex_machina.ingestion.scrapers.base_article_scraper import BaseArticleScraper
from src.hex_machina.ingestion.scrapers.playwright_mixin import PlaywrightMixin
from src.hex_machina.utils.date_parser import DateParser


class PlaywrightHtmlArticleScraper(BaseArticleScraper, PlaywrightMixin):
    """Playwright HTML scraper that handles HTML page parsing logic with Playwright."""

    def __init__(
        self,
        scraper_config,
        start_urls: Optional[List[str]] = None,
        **kwargs,
    ):
        """Initialize the PlaywrightHtmlArticleScraper.

        Args:
            scraper_config: The configuration object for this scraper (from parent).
            start_urls: List of URLs to start scraping from.
        """
        BaseArticleScraper.__init__(
            self, scraper_config=scraper_config, start_urls=start_urls, **kwargs
        )
        PlaywrightMixin.__init__(self)
        # Logger is inherited from BaseArticleScraper
        self.content_validator = create_content_validator()
        self.start_urls = start_urls

        # Configuration for HTML scraping
        self.wait_for_js = scraper_config.get("wait_for_js", 2000)
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

        return True  # True

    def _extract_article_fields(self, article, html_content):
        selector = Selector(text=html_content)
        title = self.get_title(selector)
        if not title:
            article.ingestion_error_status = "title_not_found"
            article.ingestion_error_message = "Title not found"
            title = "fake_title_" + str(datetime.now())
        article.title = title
        published_date = self.get_published_date(selector)
        published_date = DateParser.parse_date(published_date)
        if not published_date:
            article.ingestion_error_status = "published_date_not_found"
            article.ingestion_error_message = "Published date not found"
            published_date = datetime.now()
        article.published_date = published_date
        text_content = self.get_text_content(selector.get())
        if not text_content:
            article.ingestion_error_status = "text_content_not_found"
            article.ingestion_error_message = "Text content not found"
            text_content = ""
        article.text_content = text_content
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

                # Create Playwright request using the mixin
                request = await self.create_playwright_request(
                    url=link,
                    callback=self.parse_article,
                    errback=self.handle_playwright_error,
                    use_advanced_stealth=False,
                )

                yield request
                self.articles_parsed += 1
                self._logger.info(f"Parsed article: {link}")

    async def parse_article(self, response) -> ArticleModel:
        """Parse individual article page content with Playwright.

        Args:
            response: Scrapy response object

        Returns:
            ArticleModel with extracted content
        """
        page = response.meta.get("playwright_page")
        if page:
            try:
                # Check if page is still open before proceeding
                if page.is_closed():
                    self._logger.warning(f"Page already closed for {response.url}")
                    return

                html_content = await page.content()
                is_valid, validation_result = self.content_validator.validate_content(
                    html_content=html_content,
                    url=response.url,
                    status_code=response.status,
                )
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
                        "validation_result": validation_result,
                    },
                )
                self._logger.info(
                    f"Content validation for {response.url}: {validation_result}"
                )
                if not is_valid:
                    article.ingestion_error_status = "content_blocked"
                    article.ingestion_error_message = f"Content validation failed: {', '.join(validation_result['issues'])}"
                    self._logger.warning(
                        f"Blocked content detected for {article.title}: {validation_result['issues']}"
                    )
                    yield article

                captcha_selectors = [
                    ".captcha",
                    ".recaptcha",
                    ".g-recaptcha",
                    "[data-sitekey]",
                ]
                captcha_found = False
                for selector in captcha_selectors:
                    try:
                        if page.is_closed():
                            break
                        element = await page.query_selector(selector)
                        if element:
                            captcha_found = True
                            break
                    except Exception:
                        continue

                if captcha_found:
                    self._logger.warning(
                        f"CAPTCHA detected for article: {article.title}"
                    )
                    article.ingestion_error_status = "captcha_detected"
                    article.ingestion_error_message = "CAPTCHA detected"
                    article.ingestion_metadata["captcha_found"] = True

                article = self._extract_article_fields(article, html_content)

                self._logger.info(f"Successfully processed article: {response.url}")
                article.model_rebuild()
                yield article
            except Exception as e:
                error_msg = str(e)
                if "Target page, context or browser has been closed" in error_msg:
                    self._logger.warning(
                        f"Browser closed while processing {response.url}: {error_msg}"
                    )
                else:
                    self._logger.error(
                        f"Error processing page content for {response.url}: {error_msg}"
                    )
                return
            finally:
                try:
                    if page and not page.is_closed():
                        await page.close()
                except Exception as e:
                    self._logger.debug(
                        f"Error closing page for {response.url}: {str(e)}"
                    )
        else:
            self._logger.warning(
                f"Playwright page not available for {response.url}. Using fallback HTML content."
            )
            html_content = response.text
            html_content = html_content if isinstance(html_content, str) else ""
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
                ingestion_metadata={"scraper_name": self.name},
            )
            article.ingestion_error_status = "playwright_blocked"
            article.ingestion_error_message = "Playwright blocked"
            article = self._extract_article_fields(article, html_content)
            yield article
