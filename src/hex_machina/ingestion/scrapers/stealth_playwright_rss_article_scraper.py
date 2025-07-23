"""Stealth Playwright RSS article scraper for Hex Machina v2."""

import logging
import random

from playwright.async_api import async_playwright
from playwright_stealth import stealth_sync

from .rss_article_scraper import RSSArticleScraper

# Pool of realistic desktop user agents (expand as needed)
USER_AGENT_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class StealthPlaywrightRSSArticleScraper(RSSArticleScraper):
    """RSS scraper using feedparser and playwright-stealth."""

    name = "stealth_playwright_rss_article_scraper"

    def __init__(self, *args, launch_args=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logging.getLogger(f"hex_machina.scraper.{self.name}")
        config = self.scraper_config
        self.browser_type = config.get("browser_type", "chromium")
        self.headless = config.get("headless", True)
        self.launch_args = config.get("launch_args", ["--allow-file-access-from-files"])
        self.wait_until = config.get("wait_until", "networkidle")
        # Randomize viewport for each instance
        self.viewport = config.get("viewport") or {
            "width": random.randint(1200, 1920),
            "height": random.randint(700, 1080),
        }
        self.java_script_enabled = config.get("java_script_enabled", True)
        self.ignore_https_errors = config.get("ignore_https_errors", True)
        self.screenshot_on_error = config.get("screenshot_on_error", True)
        # Add realistic HTTP headers if not set
        default_headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive",
        }
        self.extra_http_headers = {
            **default_headers,
            **config.get("extra_http_headers", {}),
        }
        self.enable_stealth = config.get("enable_stealth", True)
        self.stealth_options = config.get("stealth_options", {})
        # Set locale and timezone for context
        self.locale = config.get("locale", "en-US")
        self.timezone_id = config.get("timezone_id", "America/New_York")
        self._logger.info(f"Stealth Playwright config: {config}")

    async def parse_article(self, article) -> None:
        """Async generator to scrape an article using Playwright stealth and yield a result dict.

        Args:
            article: Article object with RSS data already populated

        Yields:
            dict: Article dict with all required fields and error info if applicable
        """
        error_status = None
        error_message = None
        html_content = ""
        try:
            async with async_playwright() as p:
                user_agent = self.scraper_config.get("user_agent") or random.choice(
                    USER_AGENT_POOL
                )
                browser = await p.chromium.launch(
                    headless=self.headless, args=self.launch_args
                )
                context = await browser.new_context(
                    user_agent=user_agent,
                    locale=self.locale,
                    timezone_id=self.timezone_id,
                    viewport=self.viewport,
                    device_scale_factor=1,
                    has_touch=False,
                    is_mobile=False,
                    java_script_enabled=self.java_script_enabled,
                    ignore_https_errors=self.ignore_https_errors,
                    extra_http_headers=self.extra_http_headers,
                )
                page = await context.new_page()
                # Stealth patch (sync, but safe to call)
                stealth_sync(page)
                await page.goto(article.url, timeout=60000, wait_until=self.wait_until)
                await page.wait_for_timeout(3000)
                html_content = await page.content()
                await browser.close()
                text_content, error_status, error_message = self.parse_html(
                    html_content
                )
        except Exception as e:
            self._logger.warning(
                f"Stealth Playwright failed for {getattr(article, 'url', None)}: {e}"
            )
            error_status = "stealth_playwright_error"
            error_message = str(e)

        result = {
            "title": article.title,
            "url": article.url,
            "source_url": article.source_url,
            "url_domain": article.url_domain,
            "published_date": article.published_date,
            "html_content": html_content,
            "text_content": text_content,
            "author": getattr(article, "author", None),
            "article_metadata": getattr(article, "article_metadata", {}),
            "ingestion_metadata": {
                "scraper_name": self.name,
            },
            "ingestion_error_status": error_status,
            "ingestion_error_message": error_message,
        }
        yield result
