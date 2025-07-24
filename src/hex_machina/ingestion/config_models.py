from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ScraperConfig(BaseModel):
    """Configuration for a single scraper."""

    type: Literal[
        "playwright_rss_article_scraper", "stealth_playwright_rss_article_scraper"
    ]
    start_urls: List[str]
    browser_type: Optional[str] = None
    headless: Optional[bool] = None
    launch_args: Optional[List[str]] = None
    proxy: Optional[str] = None
    proxy_type: Optional[str] = None
    proxy_username: Optional[str] = None
    max_retries: Optional[int] = None
    screenshot_on_error: Optional[bool] = None


class ScrapyConfig(BaseModel):
    """Scrapy configuration with comprehensive settings for optimal ingestion."""

    # Basic Settings
    user_agent: Optional[str] = None
    robotstxt_obey: bool = Field(
        default=False, description="Whether to respect robots.txt"
    )

    # Performance Settings
    concurrent_requests: int = Field(
        default=16, description="Number of concurrent requests"
    )
    concurrent_requests_per_domain: int = Field(
        default=8, description="Concurrent requests per domain"
    )
    concurrent_requests_per_ip: int = Field(
        default=0, description="Concurrent requests per IP (0 = disabled)"
    )

    # Download Settings
    download_delay: float = Field(
        default=1.0, description="Delay between requests for same domain"
    )
    download_timeout: int = Field(
        default=180, description="Download timeout in seconds"
    )
    download_maxsize: int = Field(
        default=0, description="Max download size in bytes (0 = unlimited)"
    )

    # Retry Settings
    retry_enabled: bool = Field(default=True, description="Enable retry middleware")
    retry_times: int = Field(default=3, description="Number of retry attempts")
    retry_http_codes: List[int] = Field(
        default=[500, 502, 503, 504, 408, 429], description="HTTP codes to retry"
    )

    # Cache Settings
    httpcache_enabled: bool = Field(default=True, description="Enable HTTP cache")
    httpcache_expiration_secs: int = Field(
        default=3600, description="Cache expiration time"
    )
    httpcache_dir: str = Field(
        default=".scrapy/httpcache", description="Cache directory"
    )

    # Cookie Settings
    cookies_enabled: bool = Field(default=True, description="Enable cookies")

    # Compression Settings
    compression_enabled: bool = Field(default=True, description="Enable compression")

    # AutoThrottle Settings
    autothrottle_enabled: bool = Field(default=True, description="Enable AutoThrottle")
    autothrottle_start_delay: float = Field(default=1.0, description="Initial delay")
    autothrottle_max_delay: float = Field(default=60.0, description="Maximum delay")
    autothrottle_target_concurrency: float = Field(
        default=1.0, description="Target concurrency"
    )

    # Memory Settings
    memusage_enabled: bool = Field(
        default=True, description="Enable memory usage monitoring"
    )
    memusage_limit: int = Field(
        default=0, description="Memory limit in bytes (0 = unlimited)"
    )

    # Logging Settings
    log_enabled: bool = Field(default=True, description="Enable logging")
    log_stdout: bool = Field(default=False, description="Log to stdout")

    # Stats Settings
    stats_enabled: bool = Field(default=True, description="Enable stats collection")

    # Telnet Settings
    telnet_console_enabled: bool = Field(
        default=False, description="Enable telnet console"
    )

    # Custom Settings
    custom_settings: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional custom settings"
    )


class IngestionConfig(BaseModel):
    """Top-level ingestion configuration."""

    db_path: str
    articles_limit: Optional[int] = None
    date_threshold: Optional[str] = None
    log_level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR"]] = "INFO"
    scrapy: ScrapyConfig
    scrapers: List[ScraperConfig]
