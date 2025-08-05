"""Playwright mixin for common Playwright functionality in Hex Machina v2."""

import logging
import random
from typing import Any, Dict, List, Optional

import scrapy
from scrapy_playwright.page import PageMethod

# List of realistic User-Agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class PlaywrightMixin:
    """Mixin providing common Playwright functionality for scrapers."""

    def __init__(self, *args, **kwargs):
        """Initialize the Playwright mixin."""
        if not hasattr(self, "name"):
            self.name = "playwright_mixin"
        super().__init__(*args, **kwargs)
        self._playwright_logger = logging.getLogger(
            f"hex_machina.playwright.{self.name}"
        )

    def get_random_user_agent(self) -> str:
        """Get a random user agent from the predefined list.

        Returns:
            A random user agent string.
        """
        return random.choice(USER_AGENTS)

    def get_random_interactions(self) -> Dict[str, int]:
        """Generate random interaction parameters for human-like behavior.

        Returns:
            Dictionary with random interaction parameters.
        """
        return {
            "mouse_x": random.randint(0, 800),
            "mouse_y": random.randint(0, 600),
            "wheel_delta": random.randint(100, 1000),
            "delay": random.randint(500, 2000),
        }

    def get_base_playwright_page_methods(
        self, interactions: Optional[Dict[str, int]] = None
    ) -> List[PageMethod]:
        """Get base Playwright page methods for stealth and anti-detection.

        Args:
            interactions: Optional interaction parameters for human-like behavior.

        Returns:
            List of PageMethod objects for Playwright configuration.
        """
        if interactions is None:
            interactions = self.get_random_interactions()

        return [
            # Stealth: Hide webdriver
            PageMethod("wait_for_timeout", interactions["delay"]),
            PageMethod("wait_for_load_state", "networkidle"),
        ]

    def get_advanced_playwright_page_methods(
        self, interactions: Optional[Dict[str, int]] = None
    ) -> List[PageMethod]:
        """Get advanced Playwright page methods for enhanced stealth.

        Args:
            interactions: Optional interaction parameters for human-like behavior.

        Returns:
            List of PageMethod objects for advanced Playwright configuration.
        """
        base_methods = self.get_base_playwright_page_methods(interactions)

        if interactions is None:
            interactions = self.get_random_interactions()

        advanced_methods = [
            # Advanced stealth: Fake permissions
            PageMethod("wait_for_timeout", random.randint(200, 800)),
            PageMethod("wait_for_load_state", "networkidle"),
        ]

        return base_methods + advanced_methods

    def get_playwright_page_kwargs(
        self, user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get Playwright page configuration kwargs.

        Args:
            user_agent: Optional user agent string. If None, a random one will be used.

        Returns:
            Dictionary with Playwright page configuration.
        """
        if user_agent is None:
            user_agent = self.get_random_user_agent()

        return {
            "extra_http_headers": {
                "User-Agent": user_agent,  # Set user agent in headers instead of separate key
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
        }

    def get_advanced_playwright_page_kwargs(
        self, user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get advanced Playwright page configuration kwargs with additional headers.

        Args:
            user_agent: Optional user agent string. If None, a random one will be used.

        Returns:
            Dictionary with advanced Playwright page configuration.
        """
        base_kwargs = self.get_playwright_page_kwargs(user_agent)

        # Add additional stealth headers
        base_kwargs["extra_http_headers"].update(
            {
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            }
        )

        return base_kwargs

    def get_playwright_request_meta(
        self,
        callback: Any,
        errback: Any,
        article: Optional[Any] = None,
        page_methods: Optional[List[PageMethod]] = None,
        page_kwargs: Optional[Dict[str, Any]] = None,
        **additional_meta: Any,
    ) -> Dict[str, Any]:
        """Get Playwright request meta configuration.

        Args:
            callback: The callback function for the request.
            errback: The error callback function for the request.
            article: Optional article object to include in meta.
            page_methods: Optional list of PageMethod objects.
            page_kwargs: Optional page configuration kwargs.
            **additional_meta: Additional meta parameters.

        Returns:
            Dictionary with Playwright request meta configuration.
        """
        if page_methods is None:
            page_methods = self.get_base_playwright_page_methods()

        if page_kwargs is None:
            page_kwargs = self.get_playwright_page_kwargs()

        meta = {
            "playwright": True,
            "playwright_include_page": True,
            "dont_redirect": False,  # Allow redirects
            "handle_httpstatus_list": [
                301,
                302,
                307,
                308,
            ],  # Handle redirect status codes
            "playwright_page_methods": page_methods,
            "playwright_page_kwargs": page_kwargs,
            **additional_meta,
        }

        if article:
            meta["scraped_article"] = article

        return meta

    def get_playwright_headers(
        self, user_agent: Optional[str] = None
    ) -> Dict[str, str]:
        """Get headers for Playwright requests.

        Args:
            user_agent: Optional user agent string. If None, a random one will be used.

        Returns:
            Dictionary with request headers.
        """
        if user_agent is None:
            user_agent = self.get_random_user_agent()

        return {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def create_playwright_request(
        self,
        url: str,
        callback: Any,
        errback: Any,
        article: Optional[Any] = None,
        use_advanced_stealth: bool = False,
        **additional_meta: Any,
    ) -> scrapy.Request:
        """Create a Scrapy request with Playwright configuration.

        Args:
            url: The URL to request.
            callback: The callback function for the request.
            errback: The error callback function for the request.
            article: Optional article object to include in meta.
            use_advanced_stealth: Whether to use advanced stealth features.
            **additional_meta: Additional meta parameters.

        Returns:
            Scrapy Request object with Playwright configuration.
        """
        user_agent = self.get_random_user_agent()
        interactions = self.get_random_interactions()

        if use_advanced_stealth:
            page_methods = self.get_advanced_playwright_page_methods(interactions)
            page_kwargs = self.get_advanced_playwright_page_kwargs(user_agent)
        else:
            page_methods = self.get_base_playwright_page_methods(interactions)
            page_kwargs = self.get_playwright_page_kwargs(user_agent)

        meta = self.get_playwright_request_meta(
            callback=callback,
            errback=errback,
            article=article,
            page_methods=page_methods,
            page_kwargs=page_kwargs,
            **additional_meta,
        )

        headers = self.get_playwright_headers(user_agent)
        return scrapy.Request(
            url=url,
            callback=callback,
            errback=errback,
            meta=meta,
            headers=headers,
        )

    async def handle_playwright_error(self, failure: Any) -> Any:
        """
        Handle request errors and extract error information for Playwright-based scrapers.

        Args:
            failure: Scrapy failure object

        Returns:
            List containing the updated article if present, otherwise empty list.
        """
        request = failure.request
        article = request.meta.get("scraped_article")

        error_info = {
            "url": request.url,
            "error_type": str(failure.type),
            "error_message": str(failure.value),
            "article_title": getattr(article, "title", "Unknown"),
        }
        self._playwright_logger.error(f"Error processing article: {error_info}")

        # Handle specific browser disconnection errors
        if (
            "Target page, context or browser has been closed"
            in error_info["error_message"]
        ):
            self._playwright_logger.warning(
                f"Browser disconnected while processing {error_info['article_title']}: {error_info['error_message']}"
            )
        else:
            self._playwright_logger.error(
                f"Error processing article {error_info['article_title']}: {error_info['error_message']}"
            )

        # Update article with error information
        if article:
            article.ingestion_error_status = str(failure.type)
            article.ingestion_error_message = error_info["error_message"]
            article.ingestion_metadata = {
                "scraper_name": self.name,
                "error": error_info,
            }
            return [article]
        return []
