"""Tests for the PlaywrightMixin functionality."""

from unittest.mock import Mock

import pytest

from src.hex_machina.ingestion.scrapers.playwright_mixin import PlaywrightMixin


class TestPlaywrightMixin:
    """Test cases for PlaywrightMixin."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mixin = PlaywrightMixin()
        self.mixin.name = "test_scraper"

    def test_get_random_user_agent(self):
        """Test that get_random_user_agent returns a valid user agent."""
        user_agent = self.mixin.get_random_user_agent()
        assert isinstance(user_agent, str)
        assert len(user_agent) > 0
        assert "Mozilla" in user_agent

    def test_get_random_interactions(self):
        """Test that get_random_interactions returns valid interaction parameters."""
        interactions = self.mixin.get_random_interactions()

        assert isinstance(interactions, dict)
        assert "mouse_x" in interactions
        assert "mouse_y" in interactions
        assert "wheel_delta" in interactions
        assert "delay" in interactions

        assert 0 <= interactions["mouse_x"] <= 800
        assert 0 <= interactions["mouse_y"] <= 600
        assert 100 <= interactions["wheel_delta"] <= 1000
        assert 500 <= interactions["delay"] <= 2000

    def test_get_base_playwright_page_methods(self):
        """Test that get_base_playwright_page_methods returns valid PageMethod objects."""
        from scrapy_playwright.page import PageMethod

        page_methods = self.mixin.get_base_playwright_page_methods()

        assert isinstance(page_methods, list)
        assert len(page_methods) > 0

        for method in page_methods:
            assert isinstance(method, PageMethod)

    def test_get_advanced_playwright_page_methods(self):
        """Test that get_advanced_playwright_page_methods returns valid PageMethod objects."""
        from scrapy_playwright.page import PageMethod

        page_methods = self.mixin.get_advanced_playwright_page_methods()

        assert isinstance(page_methods, list)
        assert len(page_methods) > 0

        for method in page_methods:
            assert isinstance(method, PageMethod)

    def test_get_playwright_page_kwargs(self):
        """Test that get_playwright_page_kwargs returns valid configuration."""
        kwargs = self.mixin.get_playwright_page_kwargs()

        assert isinstance(kwargs, dict)
        assert "user_agent" in kwargs
        assert "viewport" in kwargs
        assert "extra_http_headers" in kwargs

        assert isinstance(kwargs["user_agent"], str)
        assert isinstance(kwargs["viewport"], dict)
        assert isinstance(kwargs["extra_http_headers"], dict)

    def test_get_advanced_playwright_page_kwargs(self):
        """Test that get_advanced_playwright_page_kwargs returns valid configuration."""
        kwargs = self.mixin.get_advanced_playwright_page_kwargs()

        assert isinstance(kwargs, dict)
        assert "user_agent" in kwargs
        assert "viewport" in kwargs
        assert "extra_http_headers" in kwargs

        # Check for additional stealth headers
        headers = kwargs["extra_http_headers"]
        assert "Sec-Fetch-Dest" in headers
        assert "Sec-Fetch-Mode" in headers
        assert "Sec-Fetch-Site" in headers
        assert "Sec-Fetch-User" in headers

    def test_get_playwright_request_meta(self):
        """Test that get_playwright_request_meta returns valid meta configuration."""
        callback = Mock()
        errback = Mock()

        meta = self.mixin.get_playwright_request_meta(
            callback=callback, errback=errback, test_param="test_value"
        )

        assert isinstance(meta, dict)
        assert meta["playwright"] is True
        assert meta["playwright_include_page"] is True
        assert meta["dont_redirect"] is False
        assert "playwright_page_methods" in meta
        assert "playwright_page_kwargs" in meta
        assert meta["test_param"] == "test_value"

    def test_get_playwright_request_meta_with_article(self):
        """Test that get_playwright_request_meta includes article in meta."""
        callback = Mock()
        errback = Mock()
        article = Mock()

        meta = self.mixin.get_playwright_request_meta(
            callback=callback, errback=errback, article=article
        )

        assert meta["scraped_article"] == article

    def test_get_playwright_headers(self):
        """Test that get_playwright_headers returns valid headers."""
        headers = self.mixin.get_playwright_headers()

        assert isinstance(headers, dict)
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "Accept-Encoding" in headers
        assert "DNT" in headers
        assert "Connection" in headers
        assert "Upgrade-Insecure-Requests" in headers

    @pytest.mark.asyncio
    async def test_create_playwright_request(self):
        """Test that create_playwright_request returns a valid Scrapy Request."""
        import scrapy

        callback = Mock()
        errback = Mock()

        request = await self.mixin.create_playwright_request(
            url="https://example.com",
            callback=callback,
            errback=errback,
            use_advanced_stealth=False,
        )

        assert isinstance(request, scrapy.Request)
        assert request.url == "https://example.com"
        assert request.callback == callback
        assert request.errback == errback
        assert request.meta["playwright"] is True

    @pytest.mark.asyncio
    async def test_create_playwright_request_with_advanced_stealth(self):
        """Test that create_playwright_request with advanced stealth works."""
        import scrapy

        callback = Mock()
        errback = Mock()

        request = await self.mixin.create_playwright_request(
            url="https://example.com",
            callback=callback,
            errback=errback,
            use_advanced_stealth=True,
        )

        assert isinstance(request, scrapy.Request)
        assert request.url == "https://example.com"
        assert request.callback == callback
        assert request.errback == errback
        assert request.meta["playwright"] is True
