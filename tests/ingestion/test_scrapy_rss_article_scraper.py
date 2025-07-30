"""Tests for ScrapyRSSArticleScraper."""

from unittest.mock import MagicMock

import pytest

from src.hex_machina.ingestion.article_models import ArticleModel
from src.hex_machina.ingestion.scrapers.scrapy_rss_article_scraper import (
    ScrapyRSSArticleScraper,
)


class TestScrapyRSSArticleScraper:
    """Test cases for ScrapyRSSArticleScraper."""

    @pytest.fixture
    def scraper_config(self):
        """Create a basic scraper configuration."""
        return {
            "name": "test_scraper",
            "start_urls": ["https://example.com/feed.xml"],
            "articles_limit": 10,
        }

    @pytest.fixture
    def scraper(self, scraper_config):
        """Create a ScrapyRSSArticleScraper instance."""
        return ScrapyRSSArticleScraper(
            scraper_config=scraper_config, start_urls=["https://example.com/feed.xml"]
        )

    @pytest.fixture
    def sample_article(self):
        """Create a sample article for testing."""
        return ArticleModel(
            title="Test Article",
            url="https://example.com/article1",
            published_date="2024-01-01T00:00:00Z",
            author="Test Author",
            summary="Test article description",
            url_domain="example.com",
            source_url="https://example.com/feed.xml",
            html_content="<html><body><h1>Test Article</h1><p>Content here</p></body></html>",
            text_content="Test Article Content here",
            article_metadata={"summary": "Test article description", "tags": []},
            ingestion_metadata={},
        )

    def test_scraper_initialization(self, scraper):
        """Test that the scraper initializes correctly."""
        assert scraper.name == "scrapy_rss_article_scraper"
        assert len(scraper.start_urls) == 1
        assert scraper.start_urls[0] == "https://example.com/feed.xml"

    def test_get_default_headers(self, scraper):
        """Test that default headers are generated correctly."""
        headers = scraper.get_default_headers("article")

        assert "Accept" in headers
        assert "User-Agent" in headers
        assert "Accept-Encoding" in headers
        assert headers["Accept-Encoding"] == "gzip, deflate"  # No Brotli

        # Test different content types
        rss_headers = scraper.get_default_headers("rss")
        assert "application/rss+xml" in rss_headers["Accept"]

        html_headers = scraper.get_default_headers("html")
        assert "text/html" in html_headers["Accept"]

    @pytest.mark.asyncio
    async def test_parse_article_creates_request(self, scraper, sample_article):
        """Test that parse_article creates a proper Scrapy request."""
        requests = []
        async for request in scraper.parse_article(sample_article):
            requests.append(request)

        assert len(requests) == 1
        request = requests[0]

        assert request.url == sample_article.url
        assert request.callback == scraper.parse
        assert request.errback == scraper.handle_error
        assert request.meta["scraped_article"] == sample_article
        assert request.meta["dont_cache"] is True
        assert request.meta["dont_retry"] is False
        assert request.dont_filter is True
        assert "User-Agent" in request.headers

    @pytest.mark.asyncio
    async def test_parse_with_valid_response(self, scraper, sample_article):
        """Test parsing a valid response."""
        # Create a mock response
        response = MagicMock()
        response.url = sample_article.url
        response.status = 200
        response.text = (
            "<html><body><h1>Test Article</h1><p>Content here</p></body></html>"
        )
        response.meta = {"scraped_article": sample_article}

        articles = []
        async for article in scraper.parse(response):
            articles.append(article)

        assert len(articles) == 1
        article = articles[0]
        assert article.html_content == response.text
        assert article.ingestion_error_status is None
        assert (
            article.ingestion_metadata["scraper_name"] == "scrapy_rss_article_scraper"
        )

    @pytest.mark.asyncio
    async def test_parse_with_successful_content(self, scraper, sample_article):
        """Test parsing successful content."""
        response = MagicMock()
        response.url = sample_article.url
        response.status = 200
        response.text = (
            "<html><body><h1>Test Article</h1><p>Content here</p></body></html>"
        )
        response.meta = {"scraped_article": sample_article}

        articles = []
        async for article in scraper.parse(response):
            articles.append(article)

        assert len(articles) == 1
        article = articles[0]
        assert article.html_content == response.text
        assert article.ingestion_error_status is None
        assert (
            article.ingestion_metadata["scraper_name"] == "scrapy_rss_article_scraper"
        )

    @pytest.mark.asyncio
    async def test_handle_error(self, scraper, sample_article):
        """Test error handling."""
        # Create a mock failure
        failure = MagicMock()
        failure.request = MagicMock()
        failure.request.url = sample_article.url
        failure.request.meta = {"scraped_article": sample_article}
        failure.type = "TimeoutError"
        failure.value = "Request timeout"

        result = await scraper.handle_error(failure)

        assert len(result) == 1
        article = result[0]
        assert article.ingestion_error_status == "TimeoutError"
        assert article.ingestion_error_message == "Request timeout"

    @pytest.mark.asyncio
    async def test_parse_with_non_200_response(self, scraper, sample_article):
        """Test parsing a non-200 response."""
        # Create a mock response with 403 status
        response = MagicMock()
        response.url = sample_article.url
        response.status = 403
        response.text = "<html><body>Access Denied</body></html>"
        response.meta = {"scraped_article": sample_article}

        articles = []
        async for article in scraper.parse(response):
            articles.append(article)

        assert len(articles) == 1
        article = articles[0]
        assert article.ingestion_error_status == "access_denied"
        assert "Forbidden - Access denied by server" in article.ingestion_error_message
        assert article.ingestion_metadata["status_code"] == 403
        assert article.ingestion_metadata["error_type"] == "http_error"

    @pytest.mark.asyncio
    async def test_parse_with_404_response(self, scraper, sample_article):
        """Test parsing a 404 response."""
        response = MagicMock()
        response.url = sample_article.url
        response.status = 404
        response.text = "<html><body>Page Not Found</body></html>"
        response.meta = {"scraped_article": sample_article}

        articles = []
        async for article in scraper.parse(response):
            articles.append(article)

        assert len(articles) == 1
        article = articles[0]
        assert article.ingestion_error_status == "not_found"
        assert (
            "Not Found - Article URL is broken or expired"
            in article.ingestion_error_message
        )
        assert article.ingestion_metadata["status_code"] == 404

    @pytest.mark.asyncio
    async def test_parse_with_500_response(self, scraper, sample_article):
        """Test parsing a 500 response."""
        response = MagicMock()
        response.url = sample_article.url
        response.status = 500
        response.text = "<html><body>Internal Server Error</body></html>"
        response.meta = {"scraped_article": sample_article}

        articles = []
        async for article in scraper.parse(response):
            articles.append(article)

        assert len(articles) == 1
        article = articles[0]
        assert article.ingestion_error_status == "server_error"
        assert (
            "Internal Server Error - Server-side issue"
            in article.ingestion_error_message
        )
        assert article.ingestion_metadata["status_code"] == 500
