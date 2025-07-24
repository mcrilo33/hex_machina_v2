from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.hex_machina.ingestion.article_models import ArticleModel
from src.hex_machina.ingestion.scrapers.playwright_rss_article_scraper import (
    USER_AGENTS,
    PlaywrightRSSArticleScraper,
)


@pytest.mark.asyncio
async def test_parse_article_yields_request():
    scraper = PlaywrightRSSArticleScraper(scraper_config={})
    article = ArticleModel(
        title="Test Title",
        url="http://example.com/article",
        published_date=datetime.now(),
        author="Author",
        summary="Summary",
        tags=[{"term": "tag1"}],
        url_domain="example.com",
        source_url="http://example.com/feed.xml",
        html_content="<html>content</html>",
        text_content="Some text content",
        article_metadata={},
        ingestion_metadata={},
    )
    reqs = [r async for r in scraper.parse_article(article)]
    assert len(reqs) == 1
    req = reqs[0]
    meta = req.meta
    assert meta["scraped_article"] == article
    assert meta["playwright"] is True
    assert meta["playwright_include_page"] is True
    assert "User-Agent" in meta["headers"]
    assert meta["headers"]["User-Agent"] in USER_AGENTS
    # Check for presence of stealth scripts and human-like actions
    page_methods = meta["playwright_page_methods"]
    assert any(pm.method == "evaluate" for pm in page_methods)
    assert any(pm.method == "add_init_script" for pm in page_methods)
    assert any(pm.method == "mouse.move" for pm in page_methods)
    assert any(pm.method == "wait_for_selector" for pm in page_methods)
    assert any(pm.method == "wait_for_load_state" for pm in page_methods)


def make_article():
    return ArticleModel(
        title="Test Title",
        url="http://example.com/article",
        published_date=datetime.now(),
        author="Author",
        summary="Summary",
        tags=[{"term": "tag1"}],
        url_domain="example.com",
        source_url="http://example.com/feed.xml",
        html_content="<html>content</html>",
        text_content="Some text content",
        article_metadata={},
        ingestion_metadata={},
    )


def make_failure(
    article=None, url="http://example.com/article", status=500, message="fail"
):
    response = MagicMock()
    response.url = url
    response.status = status
    response.meta = {"scraped_article": article} if article else {}
    failure = MagicMock()
    failure.value = Exception(message)
    failure.response = response
    return failure


def make_response(article=None, status=200, text="<html>content</html>"):
    response = MagicMock()
    response.status = status
    response.text = text
    response.meta = {"scraped_article": article} if article else {}
    return response


@pytest.mark.asyncio
async def test_handle_error_yields_article():
    scraper = PlaywrightRSSArticleScraper(scraper_config={})
    article = make_article()
    failure = make_failure(article=article, message="fail")
    result = [a async for a in scraper.handle_error(failure)]
    assert len(result) == 1
    err_article = result[0]
    assert err_article.url == failure.response.url
    assert err_article.ingestion_error_status == str(failure.response.status)
    assert err_article.ingestion_error_message
    assert err_article.ingestion_metadata["scraper_name"] == scraper.name


@pytest.mark.asyncio
async def test_parse_yields_article():
    scraper = PlaywrightRSSArticleScraper(scraper_config={})
    article = make_article()
    response = make_response(article=article, status=200, text="<html>content</html>")
    with patch.object(scraper, "parse_html", return_value=("text", None, None)):
        result = [a async for a in scraper.parse(response)]
    assert len(result) == 1
    parsed_article = result[0]
    assert parsed_article.html_content == "<html>content</html>"
    assert parsed_article.text_content == "text"
    assert parsed_article.ingestion_metadata["scraper_name"] == scraper.name


@pytest.mark.asyncio
async def test_parse_handles_error_response():
    scraper = PlaywrightRSSArticleScraper(scraper_config={})
    article = make_article()
    response = make_response(article=article, status=500, text="error")
    with patch("scrapy.spidermiddlewares.httperror.HttpError", new=Exception):

        async def fake_handle_error(failure):
            yield article

        with patch.object(scraper, "handle_error", fake_handle_error):
            result = [a async for a in scraper.parse(response)]
    assert result[0] == article
