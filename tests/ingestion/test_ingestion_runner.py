from unittest.mock import MagicMock

from src.hex_machina.ingestion.core.ingestion_runner import (
    SCRAPER_CLASS_MAP,
    IngestionRunner,
)
from src.hex_machina.ingestion.models.config_models import (
    IngestionConfig,
    ScraperConfig,
    ScrapyConfig,
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


def test_build_settings_sets_playwright_launch_options():
    config = make_config(["playwright_rss_article_scraper"])
    runner = IngestionRunner(config, DummyStorage(), crawler_process=MagicMock())
    settings = runner._build_settings()

    playwright_options = settings.get("PLAYWRIGHT_LAUNCH_OPTIONS")
    assert playwright_options is not None
    assert playwright_options.get("headless") is True
    assert playwright_options.get("timeout") == 30000
    assert "--no-sandbox" in playwright_options.get("args", [])
    assert "--disable-setuid-sandbox" in playwright_options.get("args", [])
    assert "--disable-dev-shm-usage" in playwright_options.get("args", [])
    assert "--disable-blink-features=AutomationControlled" in playwright_options.get(
        "args", []
    )
    assert "--disable-web-security" in playwright_options.get("args", [])


def test_build_settings_sets_playwright_restart_disconnected_browser():
    config = make_config(["playwright_rss_article_scraper"])
    runner = IngestionRunner(config, DummyStorage(), crawler_process=MagicMock())
    settings = runner._build_settings()

    # Should be True by default
    assert settings.get("PLAYWRIGHT_RESTART_DISCONNECTED_BROWSER") is True


def test_build_settings_sets_playwright_process_request_headers():
    config = make_config(["playwright_rss_article_scraper"])
    runner = IngestionRunner(config, DummyStorage(), crawler_process=MagicMock())
    settings = runner._build_settings()

    # Should be the custom header processing function for meaningful scraping headers
    from src.hex_machina.ingestion.core.ingestion_runner import custom_scraping_headers

    assert settings.get("PLAYWRIGHT_PROCESS_REQUEST_HEADERS") == custom_scraping_headers


def test_build_settings_uses_custom_playwright_launch_options():
    custom_options = {"headless": False, "args": ["--custom-arg", "--another-arg"]}

    config = IngestionConfig(
        db_path="test.db",
        articles_limit=5,
        date_threshold="2024-01-01",
        log_level="DEBUG",
        scrapy=ScrapyConfig(
            user_agent="test-agent", playwright_launch_options=custom_options
        ),
        scrapers=[
            ScraperConfig(
                type="playwright_rss_article_scraper", start_urls=["url1", "url2"]
            )
        ],
    )

    runner = IngestionRunner(config, DummyStorage(), crawler_process=MagicMock())
    settings = runner._build_settings()

    playwright_options = settings.get("PLAYWRIGHT_LAUNCH_OPTIONS")
    assert playwright_options is not None
    assert playwright_options.get("headless") is False
    assert "--custom-arg" in playwright_options.get("args", [])
    assert "--another-arg" in playwright_options.get("args", [])


def test_get_scraper_class_returns_correct_class():
    config = make_config(["playwright_rss_article_scraper"])
    runner = IngestionRunner(config, DummyStorage(), crawler_process=MagicMock())
    scraper_class = runner._get_scraper_class("playwright_rss_article_scraper")
    assert scraper_class == SCRAPER_CLASS_MAP["playwright_rss_article_scraper"]


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
