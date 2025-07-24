"""Playwright RSS article scraper for Hex Machina v2."""

import random
from typing import Any, Dict, Optional

import scrapy
from scrapy_playwright.page import PageMethod

from src.hex_machina.ingestion.article_models import ArticleModel
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
                        "evaluate",
                        """
                        () => {
                            const captcha = document.querySelector('iframe[src*="captcha"], .g-recaptcha, [id*="captcha"], [class*="captcha"]');
                            if (captcha) {
                                console.warn('CAPTCHA detected by Playwright!');
                            }
                        }
                        """,
                    ),
                    # Human-like mouse/keyboard actions
                    PageMethod("mouse.move", mouse_x, mouse_y),
                    PageMethod("mouse.wheel", 0, wheel_delta),
                    PageMethod("keyboard.press", "PageDown"),
                    # Resource blocking (images, media, fonts)
                    PageMethod(
                        "route",
                        "**/*",
                        """
                        (route, request) => {
                            const type = request.resourceType();
                            if ([\"image\", \"media\", \"font\"].includes(type)) {
                                route.abort();
                            } else {
                                route.continue();
                            }
                        }
                        """,
                    ),
                    # Optional: Add a small random delay to mimic human browsing
                    PageMethod("wait_for_timeout", delay),
                ],
                "playwright_context": {
                    "viewport": {"width": 1280, "height": 800},
                    "device_scale_factor": 1,
                    "is_mobile": False,
                    "has_touch": False,
                    "java_script_enabled": True,
                    # "proxy": {...},  # Uncomment and configure if you need proxies
                },
                "headers": {
                    "User-Agent": user_agent,
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                },
                "handle_httpstatus_all": True,
            },
        )

    async def handle_error(self, failure: Any) -> Dict[str, Any]:
        """Handle errors during article fetching.

        Args:
            failure: Scrapy failure object.
        Returns:
            Error ArticleModel.
        """
        try:
            error_message = str(failure.value)
        except Exception:
            error_message = str(failure)
        response = getattr(failure, "response", None)
        url = getattr(response, "url", None) if response else None
        error_status = getattr(response, "status", None) if response else None
        article = (
            response.meta.get("scraped_article")
            if response and hasattr(response, "meta")
            else None
        )
        self._logger.warning(f"Error fetching {url}: {error_message}")

        article.url = url
        article.ingestion_error_status = str(error_status)
        article.ingestion_error_message = error_message
        article.ingestion_metadata = {"scraper_name": self.name}

        yield article

    async def parse(self, response: scrapy.http.Response) -> Any:
        """Process the HTTP response and extract article content.

        Args:
            response: Scrapy response object.
        Yields:
            Article dict with extracted content or error info.
        """
        if response.status != 200:
            failure = scrapy.spidermiddlewares.httperror.HttpError(response)
            async for item in self.handle_error(failure):
                yield item
            return

        html_content = response.text if response.text else ""
        article = response.meta.get("scraped_article", None)
        text_content, error_status, error_message = self.parse_html(html_content)

        article.html_content = html_content
        article.text_content = text_content
        article.ingestion_error_status = error_status
        article.ingestion_error_message = error_message
        article.ingestion_metadata = {"scraper_name": self.name}

        yield article
