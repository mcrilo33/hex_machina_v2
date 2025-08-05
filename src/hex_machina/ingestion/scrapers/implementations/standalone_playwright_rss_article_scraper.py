"""Standalone Playwright RSS article scraper for Hex Machina v2."""

from typing import Any, Optional

import scrapy
from playwright.async_api import async_playwright

from src.hex_machina.ingestion.models.article_models import ArticleModel
from src.hex_machina.ingestion.scrapers.base.rss_article_scraper import (
    RSSArticleScraper,
)


class StandalonePlaywrightRSSArticleScraper(RSSArticleScraper):
    """Standalone scraper for articles using plain Playwright without scrapy-playwright."""

    name = "standalone_playwright_rss_article_scraper"

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
        # Initialize Playwright components
        self.playwright = None
        self.browser = None
        self.browser_type = "chromium"  # Default browser
        self.headless = True
        self.timeout = 30000  # 30 seconds timeout

        # Auto-restart configuration
        self.max_browser_restarts = 3
        self.browser_restart_count = 0
        self.max_page_retries = 2
        self.browser_restart_cooldown = 5  # seconds between restarts

    async def parse_article(self, article: ArticleModel) -> Any:
        """Process article using standalone Playwright."""

        # Create a simple Scrapy request that will trigger our custom processing
        request = scrapy.Request(
            url=article.url,
            callback=self.parse,
            errback=self.handle_error,
            meta={
                "scraped_article": article,
                "dont_retry": False,
            },
            dont_filter=True,
        )

        yield request

    async def parse(self, response: scrapy.http.Response) -> Any:
        """Parse the article content using standalone Playwright."""

        article = response.meta.get("scraped_article")
        if not article:
            self._logger.error("No article found in response meta")
            return

        self._logger.info(
            f"Processing article '{article.title}' with standalone Playwright"
        )

        try:
            # Process with standalone Playwright
            result = await self._process_with_playwright(article)
            yield result

        except Exception as e:
            self._logger.error(f"Error processing article {article.title}: {str(e)}")
            article.ingestion_error_status = "playwright_error"
            article.ingestion_error_message = str(e)
            article.ingestion_metadata = {
                "scraper_name": self.name,
                "error": str(e),
            }
            yield article

    async def _verify_and_restart_browser_if_needed(self) -> None:
        """Verify browser is alive and restart if needed."""
        if not self.browser:
            self._logger.info("Browser not initialized, starting...")
            await self._restart_browser()
            return

        try:
            # Try to create a test page to check if browser is alive
            test_page = await self.browser.new_page()
            await test_page.close()
        except Exception as e:
            self._logger.info(f"Browser appears to be dead ({str(e)}), restarting...")
            await self._restart_browser()

    async def _get_working_browser(self) -> Any:
        """Get a working browser with auto-restart capabilities."""
        for attempt in range(self.max_browser_restarts):
            try:
                if not self.browser or not await self._is_browser_alive():
                    self._logger.info(
                        f"Browser restart attempt {attempt + 1}/{self.max_browser_restarts}"
                    )
                    await self._restart_browser()
                    self.browser_restart_count += 1

                    # Add cooldown between restarts
                    if attempt > 0:
                        import asyncio

                        await asyncio.sleep(self.browser_restart_cooldown)

                # Test browser with a simple operation
                test_page = await self.browser.new_page()
                await test_page.close()
                return self.browser

            except Exception as e:
                self._logger.warning(
                    f"Browser restart attempt {attempt + 1} failed: {e}"
                )
                if attempt == self.max_browser_restarts - 1:
                    raise Exception(
                        f"Failed to get working browser after {self.max_browser_restarts} attempts"
                    )

        return self.browser

    async def _is_browser_alive(self) -> bool:
        """Check if browser is alive and responsive."""
        try:
            if not self.browser:
                return False

            # Try to create a test page to check if browser is alive
            test_page = await self.browser.new_page()
            await test_page.close()
            return True
        except Exception as e:
            self._logger.debug(f"Browser health check failed: {str(e)}")
            return False

    async def _create_page_with_retry(self) -> Any:
        """Create page with automatic retry on failure."""
        for attempt in range(self.max_page_retries):
            try:
                page = await self.browser.new_page()

                # Test if page is alive
                await page.evaluate("() => document.readyState")
                return page

            except Exception as e:
                self._logger.warning(
                    f"Page creation attempt {attempt + 1}/{self.max_page_retries} failed: {e}"
                )

                if attempt < self.max_page_retries - 1:
                    # Try to restart browser if page creation fails
                    try:
                        await self._get_working_browser()
                    except Exception as browser_error:
                        self._logger.error(
                            f"Browser restart failed during page creation: {browser_error}"
                        )
                        break
                else:
                    raise Exception(
                        f"Failed to create page after {self.max_page_retries} attempts"
                    )

    async def _verify_page_is_alive(self, page) -> bool:
        """Verify page is still alive before using it."""
        try:
            # Try a simple operation to check if page is alive
            await page.evaluate("() => document.readyState")
            return True
        except Exception as e:
            self._logger.debug(f"Page appears to be dead ({str(e)})")
            return False

    async def _process_with_playwright(self, article: ArticleModel) -> ArticleModel:
        """
        Process article using standalone Playwright.

        Args:
            article: The article to process

        Returns:
            Updated article with content
        """
        page = None

        try:
            # Initialize Playwright if not already done
            if not self.playwright:
                self.playwright = await async_playwright().start()

            # Get working browser with auto-restart
            try:
                await self._get_working_browser()
            except Exception as e:
                article.ingestion_error_status = "browser_restart_failed"
                article.ingestion_error_message = (
                    f"Failed to get working browser: {str(e)}"
                )
                article.ingestion_metadata = {
                    "scraper_name": self.name,
                    "error": str(e),
                    "error_type": "browser_restart_failed",
                    "operation": "get_working_browser",
                    "browser_restart_count": self.browser_restart_count,
                }
                return article

            # Create fresh page with retry
            try:
                page = await self._create_page_with_retry()
            except Exception as e:
                article.ingestion_error_status = "page_creation_failed"
                article.ingestion_error_message = f"Failed to create new page: {str(e)}"
                article.ingestion_metadata = {
                    "scraper_name": self.name,
                    "error": str(e),
                    "error_type": "page_creation_failed",
                    "operation": "new_page",
                    "browser_restart_count": self.browser_restart_count,
                }
                return article

            # Verify page is alive before setting headers
            if not await self._verify_page_is_alive(page):
                article.ingestion_error_status = "page_verification_failed"
                article.ingestion_error_message = "Failed to create alive page"
                article.ingestion_metadata = {
                    "scraper_name": self.name,
                    "error": "Page verification failed after creation",
                    "error_type": "page_verification_failed",
                    "operation": "page_verification",
                    "browser_restart_count": self.browser_restart_count,
                }
                return article

            # Set user agent
            try:
                await page.set_extra_http_headers(
                    {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate",
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache",
                        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                        "Sec-Ch-Ua-Mobile": "?0",
                        "Sec-Ch-Ua-Platform": '"macOS"',
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                        "Upgrade-Insecure-Requests": "1",
                        "DNT": "1",
                        "Connection": "keep-alive",
                    }
                )
            except Exception as e:
                article.ingestion_error_status = "page_verification_failed"
                article.ingestion_error_message = f"Failed to set headers: {str(e)}"
                article.ingestion_metadata = {
                    "scraper_name": self.name,
                    "error": str(e),
                    "error_type": "page_verification_failed",
                    "operation": "set_headers",
                    "browser_restart_count": self.browser_restart_count,
                }
                return article

            # Verify page is alive before navigation
            if not await self._verify_page_is_alive(page):
                article.ingestion_error_status = "page_verification_failed"
                article.ingestion_error_message = "Page died before navigation"
                article.ingestion_metadata = {
                    "scraper_name": self.name,
                    "error": "Page verification failed before navigation",
                    "error_type": "page_verification_failed",
                    "operation": "pre_navigation_verification",
                    "browser_restart_count": self.browser_restart_count,
                }
                return article

            # Navigate to the article URL with fallback strategies
            self._logger.info(f"Navigating to {article.url}")
            response = None

            # Fallback navigation strategies
            navigation_strategies = [
                {
                    "wait_until": "domcontentloaded",
                    "timeout": 10000,
                    "name": "domcontentloaded_10s",
                },
                {"wait_until": "load", "timeout": 15000, "name": "load_15s"},
                {
                    "wait_until": "networkidle",
                    "timeout": 20000,
                    "name": "networkidle_20s",
                },
                {"wait_until": None, "timeout": 5000, "name": "no_wait_5s"},
            ]

            for strategy in navigation_strategies:
                try:
                    self._logger.debug(
                        f"Trying navigation strategy: {strategy['name']}"
                    )

                    if strategy["wait_until"]:
                        response = await page.goto(
                            article.url,
                            wait_until=strategy["wait_until"],
                            timeout=strategy["timeout"],
                        )
                    else:
                        # No wait strategy - just navigate and get content immediately
                        response = await page.goto(
                            article.url, timeout=strategy["timeout"]
                        )

                    # If we get here, navigation succeeded
                    self._logger.info(
                        f"Navigation succeeded with strategy: {strategy['name']}"
                    )
                    break

                except Exception as e:
                    self._logger.debug(
                        f"Navigation strategy {strategy['name']} failed: {str(e)}"
                    )
                    if strategy == navigation_strategies[-1]:  # Last strategy
                        # All strategies failed
                        if "timeout" in str(e).lower():
                            article.ingestion_error_status = "navigation_timeout"
                            article.ingestion_error_message = (
                                f"All navigation strategies timed out: {str(e)}"
                            )
                        else:
                            article.ingestion_error_status = "navigation_failed"
                            article.ingestion_error_message = (
                                f"All navigation strategies failed: {str(e)}"
                            )
                        article.ingestion_metadata = {
                            "scraper_name": self.name,
                            "error": str(e),
                            "error_type": article.ingestion_error_status,
                            "operation": "page_goto",
                            "url": article.url,
                            "browser_restart_count": self.browser_restart_count,
                            "failed_strategies": [
                                s["name"] for s in navigation_strategies
                            ],
                        }
                        return article

            # Verify page is alive after navigation
            if not await self._verify_page_is_alive(page):
                article.ingestion_error_status = "page_verification_failed"
                article.ingestion_error_message = "Page died after navigation"
                article.ingestion_metadata = {
                    "scraper_name": self.name,
                    "error": "Page verification failed after navigation",
                    "error_type": "page_verification_failed",
                    "operation": "post_navigation_verification",
                    "url": article.url,
                    "browser_restart_count": self.browser_restart_count,
                }
                return article

            # Check response status
            if response.status != 200:
                await self._handle_non_200_response(article, response)
                return article

            # Verify page is alive before getting content
            if not await self._verify_page_is_alive(page):
                article.ingestion_error_status = "page_verification_failed"
                article.ingestion_error_message = "Page died before getting content"
                article.ingestion_metadata = {
                    "scraper_name": self.name,
                    "error": "Page verification failed before content extraction",
                    "error_type": "page_verification_failed",
                    "operation": "pre_content_verification",
                    "url": article.url,
                    "browser_restart_count": self.browser_restart_count,
                }
                return article

            # Get content quickly - no extra waiting
            try:
                html_content = await page.content()
            except Exception as e:
                article.ingestion_error_status = "content_extraction_failed"
                article.ingestion_error_message = (
                    f"Failed to extract HTML content: {str(e)}"
                )
                article.ingestion_metadata = {
                    "scraper_name": self.name,
                    "error": str(e),
                    "error_type": "content_extraction_failed",
                    "operation": "page_content",
                    "url": article.url,
                    "browser_restart_count": self.browser_restart_count,
                }
                return article

            # Success - update article with content
            article.html_content = html_content
            article.text_content = self.get_text_content(html_content)
            article.ingestion_metadata = {
                "scraper_name": self.name,
                "status_code": response.status,
                "response_size": len(html_content),
                "browser_restart_count": self.browser_restart_count,
            }

            self._logger.info(f"Successfully processed article: {article.title}")

        except Exception as e:
            self._logger.error(
                f"Error in Playwright processing for {article.title}: {str(e)}"
            )
            article.ingestion_error_status = "playwright_error"
            article.ingestion_error_message = str(e)
            article.ingestion_metadata = {
                "scraper_name": self.name,
                "error": str(e),
                "error_type": "playwright_error",
                "operation": "general_processing",
                "browser_restart_count": self.browser_restart_count,
            }

        finally:
            # Always close page immediately after use
            if page:
                try:
                    await page.close()
                except Exception as e:
                    self._logger.debug(f"Error closing page: {str(e)}")

        return article

    async def _restart_browser(self) -> None:
        """Restart browser if it's lost or closed."""
        try:
            # Close existing browser if it exists
            if self.browser:
                try:
                    await self.browser.close()
                    self._logger.info("Closed existing browser")
                except Exception as e:
                    self._logger.debug(f"Error closing existing browser: {e}")

            # Launch new browser with enhanced options
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                # Enhanced auto-restart options
                handle_sigint=True,  # Handle Ctrl+C gracefully
                handle_sigterm=True,  # Handle termination signals
                handle_sighup=True,  # Handle hangup signals
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",
                    "--disable-javascript",  # We'll enable it per page if needed
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-field-trial-config",
                    "--disable-ipc-flooding-protection",
                    "--disable-hang-monitor",  # Don't kill browser on hang
                    "--disable-prompt-on-repost",
                    "--disable-domain-reliability",
                    "--disable-component-extensions-with-background-pages",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--disable-translate",
                    "--hide-scrollbars",
                    "--mute-audio",
                    "--no-first-run",
                    "--safebrowsing-disable-auto-update",
                    "--ignore-certificate-errors",
                    "--ignore-ssl-errors",
                    "--ignore-certificate-errors-spki-list",
                    "--disable-background-networking",
                    "--disable-default-apps",
                    "--disable-extensions",
                    "--disable-sync",
                    "--disable-translate",
                    "--hide-scrollbars",
                    "--metrics-recording-only",
                    "--mute-audio",
                    "--no-first-run",
                    "--safebrowsing-disable-auto-update",
                    "--disable-client-side-phishing-detection",
                    "--disable-component-update",
                    "--disable-domain-reliability",
                ],
            )
            self._logger.info(
                f"Browser restarted successfully (restart #{self.browser_restart_count})"
            )

        except Exception as e:
            self._logger.error(f"Failed to restart browser: {str(e)}")
            raise Exception(f"browser_restart_failed: {str(e)}")

    async def _handle_non_200_response(self, article: ArticleModel, response) -> None:
        """Handle non-200 HTTP responses."""
        status_code = response.status

        status_messages = {
            403: "Forbidden - Access denied by server",
            404: "Not Found - Article URL is broken or expired",
            429: "Too Many Requests - Rate limited by server",
            500: "Internal Server Error - Server-side issue",
            502: "Bad Gateway - Server communication error",
            503: "Service Unavailable - Server temporarily unavailable",
            504: "Gateway Timeout - Server timeout",
        }

        error_message = status_messages.get(
            status_code, f"HTTP {status_code} - Unknown error"
        )

        # More specific error status mapping
        if status_code == 403:
            article.ingestion_error_status = "forbidden"
        elif status_code == 404:
            article.ingestion_error_status = "not_found"
        elif status_code == 429:
            article.ingestion_error_status = "rate_limited"
        elif status_code >= 500:
            article.ingestion_error_status = "server_error"
        elif status_code >= 400:
            article.ingestion_error_status = "client_error"
        else:
            article.ingestion_error_status = f"http_error_{status_code}"

        article.ingestion_error_message = error_message
        article.ingestion_metadata = {
            "scraper_name": self.name,
            "status_code": status_code,
            "error_type": "http_error",
            "operation": "http_response",
            "url": article.url,
        }

        self._logger.warning(
            f"HTTP {status_code} for article '{article.title}': {error_message}"
        )

        return article

    async def handle_error(self, failure: Any) -> Any:
        """Handle request errors."""
        request = failure.request
        article = request.meta.get("scraped_article")

        error_info = {
            "url": request.url,
            "error_type": str(failure.type),
            "error_message": str(failure.value),
            "article_title": getattr(article, "title", "Unknown"),
        }

        self._logger.error(
            f"Error processing article {error_info['article_title']}: {error_info['error_message']}"
        )

        if article:
            article.ingestion_error_status = str(failure.type)
            article.ingestion_error_message = error_info["error_message"]
            article.ingestion_metadata = {
                "scraper_name": self.name,
                "error": error_info,
            }
            return [article]
        return []

    async def close(self, reason: str) -> None:
        """Clean up Playwright resources."""
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                self._logger.debug(f"Error closing browser: {str(e)}")

        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                self._logger.debug(f"Error stopping Playwright: {str(e)}")
