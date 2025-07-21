"""Stealth Playwright RSS article scraper for Hex Machina v2."""

import asyncio
from typing import Optional

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

from ..models import ScrapedArticle
from .rss_article_scraper import RSSArticleScraper


class StealthPlaywrightRSSArticleScraper(RSSArticleScraper):
    """RSS scraper using feedparser and playwright-stealth."""

    name = "stealth_playwright_rss_article_scraper"

    def __init__(self, *args, launch_args=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.launch_args = launch_args or ["--allow-file-access-from-files"]
        self.logger.info(f"Playwright launch_args: {self.launch_args}")

    async def parse_article(self, article: ScrapedArticle) -> Optional[ScrapedArticle]:
        """Parse individual article content using playwright-stealth, with robust error handling.

        Args:
            article: Article object with RSS data already populated

        Returns:
            Enriched scraped article with content or error info
        """
        self.logger.debug(f"Starting stealth Playwright scraping from {article.url}")

        def scrape_with_playwright():
            try:
                with sync_playwright() as p:
                    self.logger.debug("Launching stealth Chromium browser")
                    browser = p.chromium.launch(
                        headless=True,
                        args=self.launch_args,
                    )
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        viewport={"width": 1920, "height": 1080},
                        java_script_enabled=True,
                        ignore_https_errors=True,
                    )
                    page = context.new_page()
                    stealth_sync(page)
                    self.logger.debug(f"Navigating to: {article.url}")
                    try:
                        response = page.goto(
                            article.url, wait_until="networkidle", timeout=30000
                        )
                        if response is None:
                            article.ingestion_error_status = "no_response"
                            article.ingestion_error_message = (
                                f"No response received for {article.url}"
                            )
                            return article
                        status = response.status
                        if status >= 400 or status in {301, 302, 307, 308}:
                            article.ingestion_error_status = f"http_status_{status}"
                            article.ingestion_error_message = (
                                f"HTTP status {status} for {article.url}"
                            )
                            return article
                    except Exception as e:
                        article.ingestion_error_status = "connection_error"
                        article.ingestion_error_message = str(e)
                        return article
                    page.wait_for_timeout(2000)
                    self.logger.debug("Extracting HTML content")
                    html_content = page.content()
                    if not html_content:
                        article.ingestion_error_status = "html_fetch_error"
                        article.ingestion_error_message = (
                            f"No HTML content retrieved from {article.url}"
                        )
                        return article
                    self.logger.debug(
                        f"Retrieved {len(html_content)} characters of HTML content"
                    )
                    self.logger.debug("Parsing HTML content to markdown")
                    try:
                        text_content = self.parser.parse_html(html_content)
                    except Exception as e:
                        article.ingestion_error_status = "parsing_error"
                        article.ingestion_error_message = str(e)
                        return article
                    if not text_content:
                        article.ingestion_error_status = "parsing_error"
                        article.ingestion_error_message = (
                            f"No text content extracted from {article.url}"
                        )
                        return article
                    self.logger.debug(
                        f"Extracted {len(text_content)} characters of text content"
                    )
                    article.html_content = html_content
                    article.text_content = text_content
                    self.logger.debug(
                        f"Successfully scraped article with stealth browser from {article.url}"
                    )
                    context.close()
                    browser.close()
                    return article
            except Exception as e:
                article.ingestion_error_status = "connection_or_unknown_error"
                article.ingestion_error_message = str(e)
                self.logger.error(
                    f"Error during stealth Playwright scraping of {article.url}: {e}"
                )
                return article

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, scrape_with_playwright)
