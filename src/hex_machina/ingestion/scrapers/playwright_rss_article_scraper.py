"""Playwright RSS article scraper for Hex Machina v2."""

from typing import Optional

from playwright.async_api import async_playwright

from ..models import ScrapedArticle
from .rss_article_scraper import RSSArticleScraper


class PlaywrightRSSArticleScraper(RSSArticleScraper):
    """RSS scraper using feedparser and regular playwright."""

    name = "playwright_rss_article_scraper"

    def __init__(self, *args, launch_args=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.launch_args = launch_args or ["--allow-file-access-from-files"]
        self.logger.info(f"Playwright launch_args: {self.launch_args}")

    async def parse_article(self, article: ScrapedArticle) -> Optional[ScrapedArticle]:
        """Parse individual article content using playwright, with robust error handling.

        Args:
            article: Article object with RSS data already populated

        Returns:
            Enriched scraped article with content or error info
        """
        self.logger.debug(f"Starting Playwright scraping from {article.url}")
        browser = None
        async with async_playwright() as p:
            try:
                self.logger.debug("Launching Chromium browser")
                browser = await p.chromium.launch(headless=True, args=self.launch_args)
                page = await browser.new_page()

                self.logger.debug(f"Navigating to: {article.url}")
                response = await page.goto(article.url, wait_until="networkidle")
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

                # Get raw HTML content
                self.logger.debug("Extracting HTML content")
                html_content = await page.content()

                if not html_content:
                    article.ingestion_error_status = "html_fetch_error"
                    article.ingestion_error_message = (
                        f"No HTML content retrieved from {article.url}"
                    )
                    return article

                self.logger.debug(
                    f"Retrieved {len(html_content)} characters of HTML content"
                )

                # Parse HTML content
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

                # Update article with scraped content
                article.html_content = html_content
                article.text_content = text_content

                self.logger.debug(f"Successfully scraped article from {article.url}")
                return article

            except Exception as e:
                article.ingestion_error_status = "connection_or_unknown_error"
                article.ingestion_error_message = str(e)
                self.logger.error(
                    f"Error during Playwright scraping of {article.url}: {e}"
                )
                return article
            finally:
                if browser:
                    try:
                        await browser.close()
                        self.logger.debug("Browser closed successfully")
                    except Exception as e:
                        self.logger.warning(f"Error closing browser: {e}")
