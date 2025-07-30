"""Playwright RSS article scraper for Hex Machina v2."""

from typing import Any, Optional

import scrapy

from src.hex_machina.ingestion.article_models import ArticleModel
from src.hex_machina.ingestion.scrapers.playwright_mixin import PlaywrightMixin
from src.hex_machina.ingestion.scrapers.rss_article_scraper import RSSArticleScraper


class PlaywrightRSSArticleScraper(RSSArticleScraper, PlaywrightMixin):
    """Scraper for articles using Playwright for JavaScript rendering."""

    name = "playwright_rss_article_scraper"

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
        # Logger is inherited from BaseArticleScraper

    async def parse_article(self, article: ArticleModel) -> Any:
        """Schedule a Scrapy request to parse the article content with Playwright.

        - Rotates User-Agent per request
        - Injects stealth scripts (languages, plugins, WebGL, etc.)
        - Waits for captcha selectors and logs if found
        - Simulates random human-like mouse/keyboard interactions
        - All previous anti-bot and performance options
        """
        # Create Playwright request using the mixin
        request = await self.create_playwright_request(
            url=article.url,
            callback=self.parse,
            errback=self.handle_playwright_error,
            article=article,
            use_advanced_stealth=False,
        )

        yield request

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
                # Log validation results
                # If content is blocked or invalid, mark as error
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
                    }
                else:
                    # Update article with content
                    article.html_content = html_content
                    article.text_content = self.get_text_content(html_content)
                    article.ingestion_metadata = {
                        "scraper_name": self.name,
                        "captcha_found": False,
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
            self._logger.warning(
                f"Playwright page not available for {response.url}. Using fallback HTML content."
            )
            html_content = response.text

            # Validate the content
            article.html_content = html_content
            article.text_content = self.get_text_content(html_content)
            article.ingestion_metadata = {
                "scraper_name": self.name,
            }

            self._logger.info(f"Successfully processed article: {article.title}")

        yield article
