"""Custom middleware for Hex Machina v2."""

import logging
from typing import Optional
from urllib.parse import urljoin

from scrapy import signals
from scrapy.downloadermiddlewares.redirect import RedirectMiddleware
from scrapy.http import Request, Response


class CustomRedirectMiddleware(RedirectMiddleware):
    """Enhanced redirect middleware that handles 301/302 redirects more gracefully."""

    def __init__(self, settings):
        super().__init__(settings)
        self.logger = logging.getLogger(__name__)

    def process_response(
        self, request: Request, response: Response, spider
    ) -> Optional[Response]:
        """Process response and handle redirects."""

        # Check if this is a redirect response
        if response.status in [301, 302, 307, 308]:
            self.logger.info(
                f"Handling {response.status} redirect from {request.url} to {response.headers.get('Location', 'unknown')}"
            )

            # Get the redirect URL
            redirect_url = response.headers.get("Location")
            if not redirect_url:
                self.logger.warning(
                    f"No Location header in {response.status} response from {request.url}"
                )
                return response

            # Convert to absolute URL if needed
            if not redirect_url.startswith(("http://", "https://")):
                redirect_url = urljoin(request.url, redirect_url.decode())
            else:
                redirect_url = redirect_url.decode()

            # Check if we've already followed too many redirects
            redirect_times = request.meta.get("redirect_times", 0)
            max_redirect_times = self.max_redirect_times

            if redirect_times >= max_redirect_times:
                self.logger.warning(
                    f"Max redirects ({max_redirect_times}) reached for {request.url}"
                )
                return response

            # Create new request for the redirect
            redirect_request = request.replace(
                url=redirect_url,
                meta={
                    **request.meta,
                    "redirect_times": redirect_times + 1,
                    "redirect_urls": request.meta.get("redirect_urls", [])
                    + [request.url],
                },
            )

            # Preserve original callback and errback
            redirect_request.callback = request.callback
            redirect_request.errback = request.errback

            self.logger.info(f"Following redirect: {request.url} -> {redirect_url}")
            return redirect_request

        return response


class RedirectLoggingMiddleware:
    """Middleware to log redirect information for debugging."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def process_request(self, request: Request, spider) -> None:
        """Log request information."""
        if request.meta.get("redirect_urls"):
            self.logger.info(
                f"Request with redirect history: {request.url} (redirected from: {request.meta['redirect_urls']})"
            )

    def process_response(
        self, request: Request, response: Response, spider
    ) -> Response:
        """Log response information."""
        if response.status in [301, 302, 307, 308]:
            redirect_url = response.headers.get("Location", b"").decode()
            self.logger.info(
                f"Redirect response: {response.status} {request.url} -> {redirect_url}"
            )
        return response

    def spider_opened(self, spider):
        self.logger.info(f"RedirectLoggingMiddleware enabled for spider: {spider.name}")
