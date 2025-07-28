from unittest.mock import MagicMock

from src.hex_machina.ingestion.config_models import (
    IngestionConfig,
    ScraperConfig,
    ScrapyConfig,
)
from src.hex_machina.ingestion.ingestion_runner import (
    SCRAPER_CLASS_MAP,
    IngestionRunner,
)


class DummyStorage:
    pass


def make_config(scraper_types):
    return IngestionConfig(
        db_path="test.db",
        articles_limit=5,
        date_threshold="2024-01-01",
        log_level="DEBUG",
        scrapy=ScrapyConfig(user_agent="test-agent"),
        scrapers=[
            ScraperConfig(type=stype, start_urls=["url1", "url2"])
            for stype in scraper_types
        ],
    )


def test_build_settings_sets_scrapy_and_log_level():
    config = make_config(["playwright_rss_article_scraper"])
    runner = IngestionRunner(config, DummyStorage(), crawler_process=MagicMock())
    settings = runner._build_settings()
    assert settings.get("USER_AGENT") == "test-agent"
    assert settings.get("LOG_LEVEL") == "DEBUG"
    item_pipelines = settings.get("ITEM_PIPELINES")
    # Convert BaseSettings to dict for assertion
    if hasattr(item_pipelines, "copy"):
        item_pipelines = dict(item_pipelines.copy())
    assert (
        "src.hex_machina.ingestion.scrapy_pipelines.ArticleStorePipeline"
        in item_pipelines
    )


def test_get_scraper_class_returns_correct_class():
    config = make_config(["playwright_rss_article_scraper"])
    runner = IngestionRunner(config, DummyStorage(), crawler_process=MagicMock())
    scraper_class = runner._get_scraper_class("playwright_rss_article_scraper")
    assert scraper_class == SCRAPER_CLASS_MAP["playwright_rss_article_scraper"]


def test_get_scraper_class_returns_playwright_html_article_scraper():
    config = make_config(["playwright_html_article_scraper"])
    runner = IngestionRunner(config, DummyStorage(), crawler_process=MagicMock())
    scraper_class = runner._get_scraper_class("playwright_html_article_scraper")
    assert scraper_class == SCRAPER_CLASS_MAP["playwright_html_article_scraper"]


def test_get_scraper_class_returns_deepmind_google_scraper():
    config = make_config(["deepmind_google_scraper"])
    runner = IngestionRunner(config, DummyStorage(), crawler_process=MagicMock())
    scraper_class = runner._get_scraper_class("deepmind_google_scraper")
    assert scraper_class == SCRAPER_CLASS_MAP["deepmind_google_scraper"]


def test_get_scraper_class_returns_meta_scraper():
    config = make_config(["meta_scraper"])
    runner = IngestionRunner(config, DummyStorage(), crawler_process=MagicMock())
    scraper_class = runner._get_scraper_class("meta_scraper")
    assert scraper_class == SCRAPER_CLASS_MAP["meta_scraper"]


def test_get_scraper_class_returns_microsoft_scraper():
    config = make_config(["microsoft_scraper"])
    runner = IngestionRunner(config, DummyStorage(), crawler_process=MagicMock())
    scraper_class = runner._get_scraper_class("microsoft_scraper")
    assert scraper_class == SCRAPER_CLASS_MAP["microsoft_scraper"]


def test_get_scraper_class_returns_research_google_scraper():
    config = make_config(["research_google_scraper"])
    runner = IngestionRunner(config, DummyStorage(), crawler_process=MagicMock())
    scraper_class = runner._get_scraper_class("research_google_scraper")
    assert scraper_class == SCRAPER_CLASS_MAP["research_google_scraper"]


def test_get_scraper_class_returns_synced_review_scraper():
    config = make_config(["synced_review_scraper"])
    runner = IngestionRunner(config, DummyStorage(), crawler_process=MagicMock())
    scraper_class = runner._get_scraper_class("synced_review_scraper")
    assert scraper_class == SCRAPER_CLASS_MAP["synced_review_scraper"]


def test_build_spider_kwargs_includes_all_expected_fields():
    config = make_config(["playwright_rss_article_scraper"])
    runner = IngestionRunner(config, DummyStorage(), crawler_process=MagicMock())
    scraper_cfg = config.scrapers[0]
    kwargs = runner._build_spider_kwargs(scraper_cfg)
    expected_urls = [
        f"file://{__import__('os').path.abspath('url1')}",
        f"file://{__import__('os').path.abspath('url2')}",
    ]
    assert kwargs["start_urls"] == expected_urls
