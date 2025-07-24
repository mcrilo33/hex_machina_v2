from datetime import datetime, timedelta
from unittest.mock import patch

import feedparser
import pytest

from src.hex_machina.ingestion.article_models import ArticleModel
from src.hex_machina.ingestion.scrapers.rss_article_scraper import RSSArticleScraper


class DummyRSSScraper(RSSArticleScraper):
    name = "dummy_rss_scraper"

    async def parse_article(self, article):
        yield article  # Just yield the article for testing


def make_response(text, url="http://example.com/feed.xml"):
    class Response:
        def __init__(self, text, url):
            self.text = text
            self.url = url
            self.meta = {}

    return Response(text, url)


@pytest.mark.asyncio
async def test_parse_start_url_yields_articles():
    feed_xml = """<?xml version="1.0"?>
    <rss><channel>
      <item>
        <title>Test Article</title>
        <link>http://example.com/article1</link>
        <pubDate>2025-01-01T12:00:00Z</pubDate>
      </item>
    </channel></rss>"""
    scraper = DummyRSSScraper(
        scraper_config={},
        start_urls=["http://example.com/feed.xml"],
        limit_date=None,  # Disable date filtering for the test
    )
    response = make_response(feed_xml)
    with patch("feedparser.parse", return_value=feedparser.parse(feed_xml)):
        articles = [a async for a in scraper.parse_start_url(response)]
    print(f"DEBUG: Articles yielded: {articles}")
    assert articles
    assert isinstance(articles[0], ArticleModel)
    assert articles[0].title == "Test Article"
    assert articles[0].url == "http://example.com/article1"


@pytest.mark.asyncio
async def test_parse_start_url_skips_missing_title_url():
    feed_xml = """<?xml version="1.0"?><rss><channel>
      <item>
        <link>http://example.com/article1</link>
      </item>
      <item>
        <title>Test Article</title>
      </item>
    </channel></rss>"""
    scraper = DummyRSSScraper(
        scraper_config={}, start_urls=["http://example.com/feed.xml"]
    )
    response = make_response(feed_xml)
    with patch("feedparser.parse", return_value=feedparser.parse(feed_xml)):
        articles = [a async for a in scraper.parse_start_url(response)]
    assert articles == []


@pytest.mark.asyncio
async def test_parse_start_url_skips_old_articles():
    old_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    feed_xml = f"""<?xml version="1.0"?><rss><channel>
      <item>
        <title>Old Article</title>
        <link>http://example.com/article1</link>
        <pubDate>{old_date}</pubDate>
      </item>
    </channel></rss>"""
    scraper = DummyRSSScraper(
        scraper_config={},
        start_urls=["http://example.com/feed.xml"],
        limit_date=datetime.now(),
    )
    response = make_response(feed_xml)
    with patch("feedparser.parse", return_value=feedparser.parse(feed_xml)):
        articles = [a async for a in scraper.parse_start_url(response)]
    assert articles == []
