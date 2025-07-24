import pytest
import yaml
from pydantic import ValidationError

from src.hex_machina.ingestion.config_loader import ConfigLoader
from src.hex_machina.ingestion.config_models import IngestionConfig


def write_yaml(tmp_path, content):
    file_path = tmp_path / "config.yaml"
    file_path.write_text(yaml.dump(content))
    return str(file_path)


def test_load_valid_config(tmp_path):
    config_dict = {
        "db_path": "test.db",
        "scrapy": {"user_agent": "test-agent"},
        "scrapers": [
            {"type": "playwright_rss_article_scraper", "start_urls": ["url1", "url2"]},
            {"type": "stealth_playwright_rss_article_scraper", "start_urls": ["url3"]},
        ],
        "articles_limit": 10,
        "date_threshold": "2024-01-01",
        "log_level": "DEBUG",
    }
    config_file = write_yaml(tmp_path, config_dict)
    loader = ConfigLoader(config_file)
    config = loader.load()
    assert isinstance(config, IngestionConfig)
    assert config.db_path == "test.db"
    assert config.scrapy.user_agent == "test-agent"
    assert config.scrapers[0].type == "playwright_rss_article_scraper"
    assert config.scrapers[1].type == "stealth_playwright_rss_article_scraper"
    assert config.articles_limit == 10
    assert config.date_threshold == "2024-01-01"
    assert config.log_level == "DEBUG"


def test_load_missing_required_field(tmp_path):
    config_dict = {
        # missing db_path
        "scrapy": {"user_agent": "test-agent"},
        "scrapers": [
            {"type": "playwright_rss_article_scraper", "start_urls": ["url1"]}
        ],
    }
    config_file = write_yaml(tmp_path, config_dict)
    loader = ConfigLoader(config_file)
    with pytest.raises(ValidationError) as excinfo:
        loader.load()
    assert "db_path" in str(excinfo.value)


def test_load_invalid_scraper_type(tmp_path):
    config_dict = {
        "db_path": "test.db",
        "scrapy": {"user_agent": "test-agent"},
        "scrapers": [{"type": "invalid_type", "start_urls": ["url1"]}],
    }
    config_file = write_yaml(tmp_path, config_dict)
    loader = ConfigLoader(config_file)
    with pytest.raises(ValidationError) as excinfo:
        loader.load()
    assert "type" in str(excinfo.value)
    assert "invalid_type" in str(excinfo.value)


def test_load_missing_scraper_required_field(tmp_path):
    config_dict = {
        "db_path": "test.db",
        "scrapy": {"user_agent": "test-agent"},
        "scrapers": [{"type": "playwright_rss_article_scraper"}],  # missing start_urls
    }
    config_file = write_yaml(tmp_path, config_dict)
    loader = ConfigLoader(config_file)
    with pytest.raises(ValidationError) as excinfo:
        loader.load()
    assert "start_urls" in str(excinfo.value)


def test_load_missing_scrapy_required_field(tmp_path):
    config_dict = {
        "db_path": "test.db",
        # missing scrapy
        "scrapers": [
            {"type": "playwright_rss_article_scraper", "start_urls": ["url1"]}
        ],
    }
    config_file = write_yaml(tmp_path, config_dict)
    loader = ConfigLoader(config_file)
    with pytest.raises(ValidationError) as excinfo:
        loader.load()
    assert "scrapy" in str(excinfo.value)
