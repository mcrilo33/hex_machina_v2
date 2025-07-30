#!/usr/bin/env python3
"""Basic test script to verify scrapy-playwright works with HBR URL."""

import scrapy
from scrapy_playwright.page import PageMethod


class HBRTestSpider(scrapy.Spider):
    name = "hbr_test"

    # Custom settings as recommended in the documentation
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
    }

    def start_requests(self):
        """Generate initial request with Playwright enabled."""
        url = "https://hbr.org/2025/07/the-ceo-of-kaspi-kz-on-designing-an-essential-superapp"

        yield scrapy.Request(
            url=url,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_load_state", "networkidle"),
                ],
            },
            callback=self.parse,
        )

    async def parse(self, response, **kwargs):
        """Parse the response and check if Playwright page is available."""
        page = response.meta.get("playwright_page")

        if page:
            self.logger.info("✅ Playwright page is available!")

            # Get the page content
            html_content = await page.content()
            self.logger.info(f"✅ Page content length: {len(html_content)} characters")

            # Check if we can find the title
            title = response.css("h1::text").get()
            if title:
                self.logger.info(f"✅ Found title: {title.strip()}")
            else:
                self.logger.warning("❌ No title found with CSS selector")

            # Check if we can find article content
            article_content = response.css("article, .article-content, .content").get()
            if article_content:
                self.logger.info("✅ Found article content")
            else:
                self.logger.warning("❌ No article content found")

            # Take a screenshot for debugging
            await page.screenshot(path="hbr_test_screenshot.png", full_page=True)
            self.logger.info("✅ Screenshot saved as hbr_test_screenshot.png")

            # Close the page
            await page.close()

            yield {
                "url": response.url,
                "title": title.strip() if title else None,
                "has_playwright_page": True,
                "content_length": len(html_content),
            }
        else:
            self.logger.error("❌ Playwright page is NOT available!")
            self.logger.error(f"Response meta keys: {list(response.meta.keys())}")

            yield {
                "url": response.url,
                "has_playwright_page": False,
                "error": "No playwright_page in response.meta",
            }


if __name__ == "__main__":
    # Run the spider directly
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    process = CrawlerProcess(get_project_settings())
    process.crawl(HBRTestSpider)
    process.start()
