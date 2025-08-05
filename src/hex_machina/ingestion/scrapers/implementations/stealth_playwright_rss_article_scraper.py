"""Stealth Playwright RSS article scraper for Hex Machina v2."""

from typing import Any, Optional

import scrapy

from src.hex_machina.ingestion.models.article_models import ArticleModel
from src.hex_machina.ingestion.scrapers.base.playwright_mixin import PlaywrightMixin
from src.hex_machina.ingestion.scrapers.base.rss_article_scraper import (
    RSSArticleScraper,
)


class StealthPlaywrightRSSArticleScraper(RSSArticleScraper, PlaywrightMixin):
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
        # Logger is inherited from BaseArticleScraper
        self.captcha_found = False

    async def parse_article(self, article: ArticleModel) -> Any:
        """Schedule a Scrapy request with advanced stealth features."""
        # Create Playwright request using the mixin with advanced stealth
        request = await self.create_playwright_request(
            url=article.url,
            callback=self.parse,
            errback=self.handle_error,
            article=article,
            use_advanced_stealth=True,
        )

        yield request

    async def handle_error(self, failure: Any) -> Any:
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
                    }
                else:
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
                    article.text_content = self.get_text_content(html_content)
                    article.ingestion_metadata = {
                        "scraper_name": self.name,
                        "captcha_found": False,
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

            article.html_content = html_content
            article.text_content = self.get_text_content(html_content)
            article.ingestion_metadata = {
                "scraper_name": self.name,
            }

            self._logger.info(
                f"Stealth scraper fallback processed article: {article.title}"
            )

        yield article
