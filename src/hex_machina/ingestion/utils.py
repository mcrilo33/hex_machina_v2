"""Utility functions for Hex Machina v2 ingestion."""

from pathlib import Path
from typing import Dict, List

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def load_scraping_config(config_path: str = "config/scraping_config.yaml") -> Dict:
    """Load scraping configuration from YAML file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    if not YAML_AVAILABLE:
        raise ImportError("PyYAML is required to load configuration files")

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def get_global_settings(config_path: str) -> Dict:
    """Get global settings from configuration file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Global settings dictionary
    """
    config = load_scraping_config(config_path)
    return config.get("global", {})


def get_rss_feeds_by_scraper(config_path: str) -> Dict[str, List[str]]:
    """Get RSS feeds organized by scraper type.

    Args:
        config_path: Path to the configuration file

    Returns:
        Dictionary mapping scraper types to lists of RSS feed URLs
    """
    config = load_scraping_config(config_path)
    feeds_by_scraper = {}

    # Handle the rss_feeds structure from the YAML
    rss_feeds = config.get("rss_feeds", {})

    for scraper_type, feeds in rss_feeds.items():
        if isinstance(feeds, list):
            urls = []
            for feed in feeds:
                if isinstance(feed, dict) and feed.get("enabled", True):
                    urls.append(feed["url"])
            if urls:
                feeds_by_scraper[scraper_type] = urls

    return feeds_by_scraper


def load_rss_feeds(config_path: str = "config/rss_feeds.txt") -> List[str]:
    """Load RSS feed URLs from a configuration file.

    Args:
        config_path: Path to the RSS feeds configuration file

    Returns:
        List of RSS feed URLs

    Raises:
        FileNotFoundError: If the configuration file doesn't exist
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(
            f"RSS feeds configuration file not found: {config_path}"
        )

    urls = []

    with open(config_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Validate URL format (basic check)
            if line.startswith(("http://", "https://")):
                urls.append(line)
            else:
                print(f"Warning: Invalid URL format at line {line_num}: {line}")

    return urls
