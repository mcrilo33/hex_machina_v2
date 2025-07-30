from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ScraperConfig(BaseModel):
    """Configuration for a single scraper."""

    type: Literal[
        "deepmind_google_scraper",
        "hai_scraper",
        "hbr_scraper",
        "meta_scraper",
        "microsoft_scraper",
        "research_google_scraper",
        "synced_review_scraper",
        "playwright_html_article_scraper",
        "playwright_rss_article_scraper",
        "simple_playwright_rss_article_scraper",
        "standalone_playwright_rss_article_scraper",
        "stealth_playwright_rss_article_scraper",
        "scrapy_rss_article_scraper",
    ]
    start_urls: List[str]
    articles_limit: Optional[int] = None
    max_articles_per_page: Optional[int] = None
    wait_for_js: Optional[int] = None
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
    user_agent: Optional[str] = Field(
        default=None,
        description="User agent string. Set to None when using Playwright to let browser use default",
    )
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

    # Playwright Settings
    playwright_launch_options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Playwright browser launch options. See https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch for all available options",
    )
    restart_disconnected_browser: bool = Field(
        default=True,
        description="Restart browser if it becomes disconnected during scraping",
    )
    process_request_headers: Optional[bool] = Field(
        default=None,
        description="Process request headers. Set to None to give complete control to Playwright, True to use Scrapy headers, or provide a custom function path",
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
