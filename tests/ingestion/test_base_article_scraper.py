from datetime import datetime

import pytest

from src.hex_machina.ingestion.scrapers.base_article_scraper import BaseArticleScraper


class DummyScraper(BaseArticleScraper):
    name = "dummy_scraper"

    def parse_start_url(self, response, **kwargs):
        pass

    def parse_article(self, response, **kwargs):
        pass


def test_initialization_sets_defaults():
    scraper = DummyScraper(
        limit_date=datetime(2024, 1, 1), start_urls=["url1"], scraper_config={}
    )
    assert scraper.limit_date == datetime(2024, 1, 1)
    assert scraper.start_urls == ["url1"]
    assert hasattr(scraper, "_logger")
    assert hasattr(scraper, "parser")


def test_scraper_config_is_stored():
    config = {"foo": "bar"}
    scraper = DummyScraper(scraper_config=config)
    assert scraper.scraper_config == config


def test_check_published_date_recent():
    scraper = DummyScraper(limit_date=datetime(2024, 1, 1), scraper_config={})
    recent_date = datetime(2024, 2, 1)
    assert scraper.check_published_date(recent_date) is True


def test_check_published_date_old():
    scraper = DummyScraper(limit_date=datetime(2024, 1, 1), scraper_config={})
    old_date = datetime(2023, 12, 31)
    assert scraper.check_published_date(old_date) is False


def test_parse_html_handles_valid_html():
    scraper = DummyScraper(scraper_config={})
    text, status, msg = scraper.parse_html("<html><body>Hello</body></html>")
    assert "Hello" in text
    assert status is None
    assert msg is None


def test_parse_html_handles_invalid_html(monkeypatch):
    scraper = DummyScraper(scraper_config={})
    monkeypatch.setattr(scraper.parser, "parse_html", lambda html: 1 / 0)
    text, status, msg = scraper.parse_html("<html>")
    assert status == "extract_error"
    assert msg is not None


@pytest.mark.asyncio
async def test_handle_error_logs(monkeypatch):
    scraper = DummyScraper(scraper_config={})
    logs = []
    monkeypatch.setattr(scraper._logger, "error", lambda msg: logs.append(msg))

    class DummyFailure:
        value = Exception("fail")
        response = type("Resp", (), {"url": "http://bad", "status": 404})()

    await scraper.handle_error(DummyFailure())
    assert logs


@pytest.mark.asyncio
async def test_start_yields_requests():
    scraper = DummyScraper(
        start_urls=["http://example.com/feed1", "http://example.com/feed2"],
        scraper_config={},
    )
    scraper.settings = {}  # Mock settings to avoid AttributeError
    scraper.limit_date = None  # Explicitly set to avoid AttributeError
    requests = [r async for r in scraper.start()]
    assert len(requests) == 2
    for req in requests:
        assert req.url in ["http://example.com/feed1", "http://example.com/feed2"]
        assert callable(req.callback)
        assert callable(req.errback)


def test_log_scraping_summary_logs(monkeypatch):
    scraper = DummyScraper(scraper_config={})
    logs = []
    monkeypatch.setattr(scraper._logger, "info", lambda msg: logs.append(msg))
    monkeypatch.setattr(scraper._logger, "warning", lambda msg: logs.append(msg))
    monkeypatch.setattr(scraper._logger, "debug", lambda msg: logs.append(msg))
    Article = type("Article", (), {})
    a1 = Article()
    a1.url_domain = "domain1"
    a1.title = "Title1"
    a1.url = "url1"
    a1.published_date = "2024-01-01"
    a2 = Article()
    a2.url_domain = "domain2"
    a2.title = "Title2"
    a2.url = "url2"
    a2.published_date = "2024-01-02"
    scraper._log_scraping_summary([a1, a2])
    assert any("domain1" in log or "domain2" in log for log in logs)
