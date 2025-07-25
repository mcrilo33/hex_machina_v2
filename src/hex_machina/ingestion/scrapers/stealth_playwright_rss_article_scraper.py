"""Stealth Playwright RSS article scraper with advanced anti-detection features."""

import random
from typing import Any, Dict, Optional

import scrapy
from scrapy_playwright.page import PageMethod

from src.hex_machina.ingestion.article_models import ArticleModel
from src.hex_machina.ingestion.content_validator import create_content_validator
from src.hex_machina.ingestion.scrapers.playwright_rss_article_scraper import (
    PlaywrightRSSArticleScraper,
)
from src.hex_machina.utils.logging_utils import get_logger

# List of realistic User-Agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class StealthPlaywrightRSSArticleScraper(PlaywrightRSSArticleScraper):
    """Advanced stealth scraper with retry logic and enhanced anti-detection."""

    name = "stealth_playwright_rss_article_scraper"

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
        self.captcha_found = False

    async def parse_article(self, article: ArticleModel) -> Any:
        """Schedule a Scrapy request with advanced stealth features."""
        # Get stealth options from config
        stealth_options = self.scraper_config.get("stealth_options", {})

        # Randomize User-Agent
        user_agent = random.choice(USER_AGENTS)

        # Randomize interactions
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
                    # Advanced stealth: Hide webdriver
                    PageMethod(
                        "evaluate",
                        "() => Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                    ),
                    # Advanced stealth: Fake languages
                    PageMethod(
                        "add_init_script",
                        "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});",
                    ),
                    # Advanced stealth: Fake plugins
                    PageMethod(
                        "add_init_script",
                        "Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});",
                    ),
                    # Advanced stealth: Fake WebGL vendor/renderer
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
                    # Advanced stealth: Fake permissions
                    PageMethod(
                        "add_init_script",
                        """
                        Object.defineProperty(navigator, 'permissions', {
                            get: () => ({
                                query: () => Promise.resolve({ state: 'granted' })
                            })
                        });
                        """,
                    ),
                    # Advanced stealth: Fake notifications
                    PageMethod(
                        "add_init_script",
                        """
                        Object.defineProperty(Notification, 'permission', {
                            get: () => 'granted'
                        });
                        """,
                    ),
                    # Wait for main content or network idle
                    PageMethod(
                        "wait_for_selector",
                        "article, .main-content, .post, [role=main]",
                    ),
                    PageMethod("wait_for_load_state", "networkidle"),
                    # Enhanced captcha detection
                    PageMethod(
                        "wait_for_selector",
                        ".captcha, .recaptcha, .g-recaptcha, [data-sitekey], .h-captcha",
                        timeout=2000,
                    ),
                    # Advanced human-like interactions
                    PageMethod(
                        "mouse_move",
                        x=mouse_x,
                        y=mouse_y,
                    ),
                    PageMethod("wheel", delta_y=wheel_delta),
                    PageMethod("wait_for_timeout", delay),
                    # Random scrolling
                    PageMethod(
                        "evaluate",
                        f"() => window.scrollTo(0, {random.randint(100, 500)})",
                    ),
                    PageMethod("wait_for_timeout", random.randint(200, 800)),
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
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
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
        """Handle request errors with enhanced logging."""
        request = failure.request
        article = request.meta.get("scraped_article")

        error_info = {
            "url": request.url,
            "error_type": str(failure.type),
            "error_message": str(failure.value),
            "article_title": getattr(article, "title", "Unknown"),
        }

        self._logger.error(
            f"Stealth scraper error for {error_info['article_title']}: {error_info['error_message']}"
        )

        # Update article with error information
        if article:
            article.ingestion_error_status = error_info["error_type"]
            article.ingestion_error_message = error_info["error_message"]
            article.ingestion_metadata = {
                "scraper_name": self.name,
                "error": error_info,
            }

        return error_info

    async def parse(self, response: scrapy.http.Response) -> Any:
        """Parse the article content with enhanced validation and stealth features."""
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

                # Enhanced content validation for stealth scenarios
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
                    f"Stealth content validation for {article.title}: {validation_summary}"
                )

                # If content is blocked or invalid, mark as error
                if not is_valid:
                    article.ingestion_error_status = "content_blocked"
                    article.ingestion_error_message = f"Stealth content validation failed: {', '.join(validation_result['issues'])}"
                    article.ingestion_metadata = {
                        "scraper_name": self.name,
                        "validation_result": validation_result,
                    }
                    self._logger.warning(
                        f"Stealth blocked content detected for {article.title}: {validation_result['issues']}"
                    )
                    return

                # Enhanced captcha detection
                captcha_selectors = [
                    ".captcha",
                    ".recaptcha",
                    ".g-recaptcha",
                    "[data-sitekey]",
                    ".h-captcha",
                    "iframe[src*='captcha']",
                    "[class*='captcha']",
                ]
                captcha_found = False
                for selector in captcha_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            captcha_found = True
                            self.captcha_found = True
                            break
                    except Exception:
                        continue

                if captcha_found:
                    self._logger.warning(
                        f"CAPTCHA detected by stealth scraper for article: {article.title}"
                    )
                    article.ingestion_metadata = {
                        "scraper_name": self.name,
                        "captcha_found": True,
                        "validation_result": validation_result,
                    }
                else:
                    # Extract text content with enhanced method
                    text_content = await page.evaluate("() => document.body.innerText")

                    # Additional stealth checks
                    suspicious_elements = await page.query_selector_all(
                        "script[src*='bot'], script[src*='captcha']"
                    )
                    if suspicious_elements:
                        self._logger.warning(
                            f"Suspicious elements detected for {article.title}"
                        )

                    # Update article with content
                    article.html_content = html_content
                    article.text_content = text_content
                    article.ingestion_metadata = {
                        "scraper_name": self.name,
                        "captcha_found": False,
                        "validation_result": validation_result,
                        "suspicious_elements": len(suspicious_elements),
                    }

                    self._logger.info(
                        f"Stealth scraper successfully processed article: {article.title}"
                    )

            except Exception as e:
                self._logger.error(
                    f"Stealth scraper error processing page content for {article.title}: {str(e)}"
                )
                article.ingestion_error_status = "stealth_page_processing_error"
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
                article.ingestion_error_message = f"Stealth content validation failed: {', '.join(validation_result['issues'])}"
                article.ingestion_metadata = {
                    "scraper_name": self.name,
                    "validation_result": validation_result,
                }
                self._logger.warning(
                    f"Stealth blocked content detected for {article.title}: {validation_result['issues']}"
                )
                return

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

            self._logger.info(
                f"Stealth scraper fallback processed article: {article.title}"
            )

        yield article
