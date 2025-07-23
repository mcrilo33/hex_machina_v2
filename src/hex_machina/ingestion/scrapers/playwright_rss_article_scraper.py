"""Playwright RSS article scraper for Hex Machina v2."""

import logging
from datetime import datetime
from typing import Optional

import scrapy
from scrapy_playwright.page import PageMethod

from .rss_article_scraper import RSSArticleScraper


class PlaywrightRSSArticleScraper(RSSArticleScraper):
    name = "playwright_rss_article_scraper"

    def __init__(
        self,
        processed_limit: int = 100,
        limit_date: Optional[datetime] = None,
        start_urls: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(
            processed_limit=processed_limit,
            limit_date=limit_date,
            start_urls=start_urls,
            **kwargs,
        )
        self._logger = logging.getLogger(f"hex_machina.scraper.{self.name}")

    async def parse_article(self, article) -> None:
        """Schedule a Scrapy request to parse the article content with Playwright.

        Args:
            article (Article): The article object to be scraped.
        """
        self.article = article
        yield scrapy.Request(
            url=article.url,
            callback=self.parse,
            errback=self.handle_error,
            meta={
                "scraped_article": article,
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    PageMethod(
                        "evaluate",
                        "() => Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                    ),
                    PageMethod("wait_for_timeout", 2000),
                ],
                "handle_httpstatus_all": True,
            },
        )

    def handle_error(self, failure):
        error_status = "request_error"
        try:
            error_message = str(failure.value)
        except Exception:
            error_message = str(failure)
        response = getattr(failure, "response", None)
        url = getattr(response, "url", None) if response else None
        error_status = getattr(response, "status", None) if response else None

        self._logger.warning(f"Error fetching {url}: {error_message}")

        article = {
            "title": self.article.title,
            "url": url,
            "source_url": self.article.source_url,
            "url_domain": self.article.url_domain,
            "published_date": self.article.published_date,
            "html_content": "",
            "text_content": "",
            "author": self.article.author,
            "article_metadata": self.article.article_metadata,
            "ingestion_metadata": {
                "scraper_name": self.name,
            },
            "ingestion_error_status": str(error_status),
            "ingestion_error_message": error_message,
        }
        self.processed_counter += 1
        yield article

    def parse(self, response) -> None:
        """Callback to process the HTTP response and extract article content.

        Args:
            response: Scrapy response object.
        """
        if response.status != 200:
            failure = scrapy.spidermiddlewares.httperror.HttpError(response)
            for item in self.handle_error(failure):
                yield item
            return

        html_content = response.text if response.text else ""
        scraped_article = response.meta.get("scraped_article", {})
        text_content, error_status, error_message = self.parse_html(html_content)
        article = {
            "title": scraped_article.title,
            "url": scraped_article.url,
            "source_url": scraped_article.source_url,
            "url_domain": scraped_article.url_domain,
            "published_date": scraped_article.published_date,
            "html_content": html_content,
            "text_content": text_content,
            "author": scraped_article.author,
            "article_metadata": scraped_article.article_metadata,
            "ingestion_metadata": {
                "scraper_name": self.name,
            },
            "ingestion_error_status": error_status,
            "ingestion_error_message": error_message,
        }

        self.processed_counter += 1
        yield article
