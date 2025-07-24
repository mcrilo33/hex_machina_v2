from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.hex_machina.ingestion.article_models import ArticleModel
from src.hex_machina.ingestion.scrapers.stealth_playwright_rss_article_scraper import (
    StealthPlaywrightRSSArticleScraper,
)


@pytest.mark.asyncio
async def test_parse_article_yields_articlemodel(monkeypatch):
    # Mock Playwright and stealth_async
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_page.content.return_value = "<html>content</html>"
    mock_page.query_selector.return_value = None
    mock_context.new_page.return_value = mock_page
    mock_browser.new_context.return_value = mock_context
    mock_playwright = MagicMock()
    setattr(
        mock_playwright,
        "chromium",
        MagicMock(launch=AsyncMock(return_value=mock_browser)),
    )
    monkeypatch.setattr(
        "playwright.async_api.async_playwright", AsyncMock(return_value=mock_playwright)
    )
    monkeypatch.setattr(
        "src.hex_machina.ingestion.scrapers.stealth_playwright_rss_article_scraper.stealth_async",
        AsyncMock(),
    )

    scraper = StealthPlaywrightRSSArticleScraper(scraper_config={})
    article = ArticleModel(
        title="Test Title",
        url="http://example.com/article",
        published_date=datetime.now(),
        author="Author",
        summary="Summary",
        tags=[{"term": "tag1"}],
        url_domain="example.com",
        source_url="http://example.com/feed.xml",
        html_content="",
        text_content="",
        article_metadata={},
        ingestion_metadata={},
    )
    # Patch parse_html to return dummy text and no error
    monkeypatch.setattr(scraper, "parse_html", lambda html: ("text", None, None))
    result = [a async for a in scraper.parse_article(article)]
    assert len(result) == 1
    out = result[0]
    assert isinstance(out, ArticleModel)
    assert "<html" in out.html_content
    assert out.text_content == "text"
    assert out.ingestion_metadata["scraper_name"] == scraper.name
    assert out.ingestion_metadata["captcha_found"] is False


@pytest.mark.asyncio
async def test_parse_article_retry_success(monkeypatch):
    # Simulate failure on first attempt, success on second
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_page.content.side_effect = [Exception("fail"), "<html>ok</html>"]
    mock_page.query_selector.return_value = None
    mock_context.new_page.return_value = mock_page
    mock_browser.new_context.return_value = mock_context
    mock_playwright = MagicMock()
    setattr(
        mock_playwright,
        "chromium",
        MagicMock(launch=AsyncMock(return_value=mock_browser)),
    )
    monkeypatch.setattr(
        "playwright.async_api.async_playwright", AsyncMock(return_value=mock_playwright)
    )
    monkeypatch.setattr(
        "src.hex_machina.ingestion.scrapers.stealth_playwright_rss_article_scraper.stealth_async",
        AsyncMock(),
    )

    scraper = StealthPlaywrightRSSArticleScraper(scraper_config={"max_retries": 2})
    article = ArticleModel(
        title="Test Title",
        url="http://example.com/article",
        published_date=datetime.now(),
        author="Author",
        summary="Summary",
        tags=[{"term": "tag1"}],
        url_domain="example.com",
        source_url="http://example.com/feed.xml",
        html_content="",
        text_content="",
        article_metadata={},
        ingestion_metadata={},
    )
    monkeypatch.setattr(scraper, "parse_html", lambda html: ("text", None, None))
    result = [a async for a in scraper.parse_article(article)]
    assert "<html" in result[0].html_content
    assert result[0].ingestion_error_status is None
    assert result[0].ingestion_metadata["captcha_found"] is False


@pytest.mark.asyncio
async def test_parse_article_playwright_error(monkeypatch):
    # Simulate Playwright error and screenshot on error
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_page.content.side_effect = Exception("fail")
    mock_page.query_selector.return_value = None
    mock_page.screenshot = AsyncMock()
    mock_context.new_page.return_value = mock_page
    mock_browser.new_context.return_value = mock_context
    mock_playwright = MagicMock()
    setattr(
        mock_playwright,
        "chromium",
        MagicMock(launch=AsyncMock(return_value=mock_browser)),
    )
    monkeypatch.setattr(
        "playwright.async_api.async_playwright", AsyncMock(return_value=mock_playwright)
    )
    monkeypatch.setattr(
        "src.hex_machina.ingestion.scrapers.stealth_playwright_rss_article_scraper.stealth_async",
        AsyncMock(),
    )

    scraper = StealthPlaywrightRSSArticleScraper(
        scraper_config={"screenshot_on_error": True, "max_retries": 1}
    )
    article = ArticleModel(
        title="Test Title",
        url="http://example.com/article",
        published_date=datetime.now(),
        author="Author",
        summary="Summary",
        tags=[{"term": "tag1"}],
        url_domain="example.com",
        source_url="http://example.com/feed.xml",
        html_content="",
        text_content="",
        article_metadata={},
        ingestion_metadata={},
    )
    monkeypatch.setattr(
        scraper, "parse_html", lambda html: ("", "stealth_playwright_error", "fail")
    )
    result = [a async for a in scraper.parse_article(article)]
    assert result[0].ingestion_error_status == "stealth_playwright_error"
    assert result[0].ingestion_error_message == "fail"
    assert result[0].ingestion_metadata["captcha_found"] is False
