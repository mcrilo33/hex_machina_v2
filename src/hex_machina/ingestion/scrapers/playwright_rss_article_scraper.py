"""Playwright RSS article scraper for Hex Machina v2."""

import random
from typing import Any, Dict, Optional

import scrapy
from scrapy_playwright.page import PageMethod

from src.hex_machina.ingestion.article_models import ArticleModel
from src.hex_machina.ingestion.content_validator import create_content_validator
from src.hex_machina.ingestion.scrapers.rss_article_scraper import RSSArticleScraper
from src.hex_machina.utils.logging_utils import get_logger

# List of realistic User-Agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class PlaywrightRSSArticleScraper(RSSArticleScraper):
    """Scraper for articles using Playwright for JavaScript rendering."""

    name = "playwright_rss_article_scraper"

    def __init__(
        self,
        scraper_config: dict,
        start_urls: Optional[list] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            scraper_config=scraper_config,
            start_urls=start_urls,
            **kwargs,
        )
        self._logger = get_logger(f"hex_machina.scraper.{self.name}")
        self.content_validator = create_content_validator()

    async def parse_article(self, article: ArticleModel) -> Any:
        """Schedule a Scrapy request to parse the article content with Playwright.

        - Rotates User-Agent per request
        - Injects stealth scripts (languages, plugins, WebGL, etc.)
        - Waits for captcha selectors and logs if found
        - Simulates random human-like mouse/keyboard interactions
        - All previous anti-bot and performance options
        """
        # Randomize User-Agent
        user_agent = random.choice(USER_AGENTS)
        # Randomize mouse movement and delay
        mouse_x = random.randint(0, 800)
        mouse_y = random.randint(0, 600)
        wheel_delta = random.randint(100, 1000)
        delay = random.randint(500, 2000)

        yield scrapy.Request(
            url=article.url,
            callback=self.parse,
            errback=self.handle_error,
            meta={
                "scraped_article": article,
                "playwright": True,
                "playwright_include_page": True,
                "dont_redirect": False,  # Allow redirects
                "handle_httpstatus_list": [
                    301,
                    302,
                    307,
                    308,
                ],  # Handle redirect status codes
                "playwright_page_methods": [
                    # Stealth: Hide webdriver
                    PageMethod(
                        "evaluate",
                        "() => Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                    ),
                    # Stealth: Fake languages
                    PageMethod(
                        "add_init_script",
                        "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});",
                    ),
                    # Stealth: Fake plugins
                    PageMethod(
                        "add_init_script",
                        "Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});",
                    ),
                    # Stealth: Fake WebGL vendor/renderer
                    PageMethod(
                        "add_init_script",
                        """
                        const getParameter = WebGLRenderingContext.prototype.getParameter;
                        WebGLRenderingContext.prototype.getParameter = function(parameter) {
                            if (parameter === 37445) { return 'Intel Inc.'; }
                            if (parameter === 37446) { return 'Intel Iris OpenGL Engine'; }
                            return getParameter(parameter);
                        };
                        """,
                    ),
                    # Wait for main content or network idle
                    PageMethod(
                        "wait_for_selector",
                        "article, .main-content, .post, [role=main]",
                    ),
                    PageMethod("wait_for_load_state", "networkidle"),
                    # Captcha detection: wait for known captcha selectors (log if found)
                    PageMethod(
                        "wait_for_selector",
                        ".captcha, .recaptcha, .g-recaptcha, [data-sitekey]",
                        timeout=2000,
                    ),
                    # Human-like interactions
                    PageMethod(
                        "mouse_move",
                        x=mouse_x,
                        y=mouse_y,
                    ),
                    PageMethod("wheel", delta_y=wheel_delta),
                    PageMethod("wait_for_timeout", delay),
                ],
                "playwright_page_kwargs": {
                    "user_agent": user_agent,
                    "viewport": {"width": 1920, "height": 1080},
                    "extra_http_headers": {
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    },
                },
            },
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
        )

    async def handle_error(self, failure: Any) -> Dict[str, Any]:
        """Handle request errors and extract error information."""
        request = failure.request
        article = request.meta.get("scraped_article")

        error_info = {
            "url": request.url,
            "error_type": str(failure.type),
            "error_message": str(failure.value),
            "article_title": getattr(article, "title", "Unknown"),
        }

        self._logger.error(
            f"Error processing article {error_info['article_title']}: {error_info['error_message']}"
        )

        # Update article with error information
        if article:
            article.ingestion_error_status = error_info["error_type"]
            article.ingestion_error_message = error_info["error_message"]
            article.ingestion_metadata = {
                "scraper_name": self.name,
                "error": error_info,
            }

        yield article

    async def parse(self, response: scrapy.http.Response) -> Any:
        """Parse the article content and validate it."""
        article = response.meta.get("scraped_article")
        if not article:
            self._logger.error("No article found in response meta")
            return

        # Get HTML content from Playwright page
        page = response.meta.get("playwright_page")
        if page:
            try:
                # Get the full HTML content
                html_content = await page.content()

                # Validate the content for blocking/anti-bot detection
                is_valid, validation_result = self.content_validator.validate_content(
                    html_content=html_content,
                    url=response.url,
                    status_code=response.status,
                )

                # Log validation results
                validation_summary = self.content_validator.extract_validation_summary(
                    validation_result
                )
                self._logger.info(
                    f"Content validation for {article.title}: {validation_summary}"
                )

                # If content is blocked or invalid, mark as error
                if not is_valid:
                    article.ingestion_error_status = "content_blocked"
                    article.ingestion_error_message = f"Content validation failed: {', '.join(validation_result['issues'])}"
                    article.ingestion_metadata = {
                        "scraper_name": self.name,
                        "validation_result": validation_result,
                    }
                    self._logger.warning(
                        f"Blocked content detected for {article.title}: {validation_result['issues']}"
                    )
                    yield article

                # Check for captcha detection
                captcha_selectors = [
                    ".captcha",
                    ".recaptcha",
                    ".g-recaptcha",
                    "[data-sitekey]",
                ]
                captcha_found = False
                for selector in captcha_selectors:
                    try:
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
                    article.ingestion_metadata = {
                        "scraper_name": self.name,
                        "captcha_found": True,
                        "validation_result": validation_result,
                    }
                else:
                    # Extract text content
                    text_content = await page.evaluate("() => document.body.innerText")

                    # Update article with content
                    article.html_content = html_content
                    article.text_content = text_content
                    article.ingestion_metadata = {
                        "scraper_name": self.name,
                        "captcha_found": False,
                        "validation_result": validation_result,
                    }

                    self._logger.info(
                        f"Successfully processed article: {article.title}"
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
            # Fallback to regular Scrapy response
            html_content = response.text

            # Validate the content
            is_valid, validation_result = self.content_validator.validate_content(
                html_content=html_content, url=response.url, status_code=response.status
            )

            if not is_valid:
                article.ingestion_error_status = "content_blocked"
                article.ingestion_error_message = f"Content validation failed: {', '.join(validation_result['issues'])}"
                article.ingestion_metadata = {
                    "scraper_name": self.name,
                    "validation_result": validation_result,
                }
                self._logger.warning(
                    f"Blocked content detected for {article.title}: {validation_result['issues']}"
                )
                yield article

            # Extract text content using basic method
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")
            text_content = soup.get_text(separator=" ", strip=True)

            article.html_content = html_content
            article.text_content = text_content
            article.ingestion_metadata = {
                "scraper_name": self.name,
                "validation_result": validation_result,
            }

            self._logger.info(f"Successfully processed article: {article.title}")

        yield article
