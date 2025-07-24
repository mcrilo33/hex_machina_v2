"""Stealth Playwright RSS article scraper for Hex Machina v2."""

import random
from datetime import datetime
from typing import AsyncGenerator, Optional

from playwright.async_api import BrowserContext, Page, async_playwright
from playwright_stealth import stealth_async

from src.hex_machina.ingestion.article_models import ArticleModel
from src.hex_machina.ingestion.scrapers.rss_article_scraper import RSSArticleScraper
from src.hex_machina.utils.logging_utils import get_logger

# Pool of realistic desktop user agents (expand as needed)
USER_AGENT_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class StealthPlaywrightRSSArticleScraper(RSSArticleScraper):
    """RSS scraper using feedparser and playwright-stealth with advanced anti-bot features."""

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
        self.browser_type = self.scraper_config.get("browser_type", "chromium")
        self.headless = self.scraper_config.get("headless", True)
        self.launch_args = self.scraper_config.get(
            "launch_args", ["--allow-file-access-from-files"]
        )
        self.proxy = self.scraper_config.get("proxy")
        self.max_retries = self.scraper_config.get("max_retries", 2)
        self.screenshot_on_error = self.scraper_config.get("screenshot_on_error", True)
        self.captcha_found = False
        self._logger.info(f"Stealth Playwright config: {self.scraper_config}")

    async def parse_article(
        self, article: ArticleModel
    ) -> AsyncGenerator[ArticleModel, None]:
        """Async generator to scrape an article using Playwright stealth and yield an ArticleModel.

        Args:
            article: ArticleModel with RSS data already populated
        Yields:
            ArticleModel with all required fields and error info if applicable
        """
        error_status = None
        error_message = None
        html_content = ""
        text_content = ""
        # Standardized context options
        viewport = {
            "width": random.randint(1200, 1920),
            "height": random.randint(700, 1080),
        }
        locale = "en-US"
        timezone_id = "America/New_York"
        extra_http_headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive",
        }
        device_scale_factor = 1
        has_touch = False
        is_mobile = False
        java_script_enabled = True
        ignore_https_errors = True
        wait_until = "networkidle"
        for attempt in range(1, self.max_retries + 1):
            try:
                async with async_playwright() as p:
                    user_agent = self.scraper_config.get("user_agent") or random.choice(
                        USER_AGENT_POOL
                    )
                    browser = await getattr(p, self.browser_type).launch(
                        headless=self.headless, args=self.launch_args
                    )
                    context_args = dict(
                        user_agent=user_agent,
                        locale=locale,
                        timezone_id=timezone_id,
                        viewport=viewport,
                        device_scale_factor=device_scale_factor,
                        has_touch=has_touch,
                        is_mobile=is_mobile,
                        java_script_enabled=java_script_enabled,
                        ignore_https_errors=ignore_https_errors,
                        extra_http_headers=extra_http_headers,
                    )
                    if self.proxy:
                        context_args["proxy"] = self.proxy
                    context: BrowserContext = await browser.new_context(**context_args)
                    page: Page = await context.new_page()
                    # Stealth patch (async)
                    await stealth_async(page)
                    # Block images, fonts, media
                    await page.route(
                        "**/*",
                        lambda route, request: (
                            route.abort()
                            if request.resource_type in ["image", "media", "font"]
                            else route.continue_()
                        ),
                    )
                    # Human-like actions
                    mouse_x = random.randint(0, 800)
                    mouse_y = random.randint(0, 600)
                    wheel_delta = random.randint(100, 1000)
                    await page.mouse.move(mouse_x, mouse_y)
                    await page.mouse.wheel(0, wheel_delta)
                    await page.keyboard.press("PageDown")
                    # Go to page
                    await page.goto(article.url, timeout=60000, wait_until=wait_until)
                    await page.wait_for_timeout(random.randint(1000, 3000))
                    html_content = await page.content()
                    # Captcha detection
                    self.captcha_found = (
                        await page.query_selector(
                            'iframe[src*="captcha"], .g-recaptcha, [id*="captcha"], [class*="captcha"]'
                        )
                        is not None
                    )
                    if self.captcha_found:
                        self._logger.warning(f"CAPTCHA detected on {article.url}")
                    await browser.close()
                    text_content, error_status, error_message = self.parse_html(
                        html_content
                    )
                    break  # Success, exit retry loop
            except Exception as e:
                self._logger.warning(
                    f"Stealth Playwright failed for {getattr(article, 'url', None)} (attempt {attempt}): {e}"
                )
                error_status = "stealth_playwright_error"
                error_message = str(e)
                if self.screenshot_on_error and "page" in locals():
                    try:
                        await page.screenshot(
                            path=f"error_{self.name}_{int(datetime.now().timestamp())}.png"
                        )
                    except Exception as se:
                        self._logger.warning(f"Screenshot on error failed: {se}")
                if attempt == self.max_retries:
                    break
        article.html_content = html_content
        article.text_content = text_content
        article.ingestion_error_status = error_status
        article.ingestion_error_message = error_message
        article.ingestion_metadata = {
            "scraper_name": self.name,
            "captcha_found": self.captcha_found,
        }
        yield article
