#!/usr/bin/env python3
"""Test script to verify the simplified playwright setup works."""

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from src.hex_machina.ingestion.scrapers.html_article_scrapers.hbr_scraper import (
    HBRScraper,
)


class TestHBRSpider(HBRScraper):
    """Test spider using the simplified HBR scraper."""

    name = "test_hbr"

    custom_settings = {
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "DOWNLOAD_HANDLERS": {
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        },
        "PLAYWRIGHT_INCLUDE_PAGE": True,
        "INGESTION_DATE_THRESHOLD": "2025-07-27",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(
            scraper_config={
                "wait_for_js": 2000,
                "max_articles_per_page": 1,
                "articles_limit": 1,
            },
            start_urls=["https://hbr.org/the-latest"],
            **kwargs,
        )


if __name__ == "__main__":
    # Run the spider directly
    process = CrawlerProcess(get_project_settings())
    process.crawl(TestHBRSpider)
    process.start()
