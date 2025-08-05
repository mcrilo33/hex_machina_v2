import logging
import signal
import sys
from typing import Any, Dict

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from src.hex_machina.ingestion.models.config_models import IngestionConfig
from src.hex_machina.ingestion.scrapers.html_article_scrapers.deepmind_google_scraper import (
    DeepMindGoogleScraper,
)
from src.hex_machina.ingestion.scrapers.html_article_scrapers.hai_scraper import (
    HAIScraper,
)
from src.hex_machina.ingestion.scrapers.html_article_scrapers.hbr_scraper import (
    HBRScraper,
)
from src.hex_machina.ingestion.scrapers.html_article_scrapers.meta_scraper import (
    MetaScraper,
)
from src.hex_machina.ingestion.scrapers.html_article_scrapers.microsoft_scraper import (
    MicrosoftScraper,
)
from src.hex_machina.ingestion.scrapers.html_article_scrapers.research_google_scraper import (
    ResearchGoogleScraper,
)
from src.hex_machina.ingestion.scrapers.html_article_scrapers.synced_review_scraper import (
    SyncedReviewScraper,
)
from src.hex_machina.ingestion.scrapers.implementations.playwright_rss_article_scraper import (
    PlaywrightRSSArticleScraper,
)
from src.hex_machina.ingestion.scrapers.implementations.scrapy_rss_article_scraper import (
    ScrapyRSSArticleScraper,
)
from src.hex_machina.ingestion.scrapers.implementations.simple_playwright_rss_article_scraper import (
    SimplePlaywrightRSSArticleScraper,
)
from src.hex_machina.ingestion.scrapers.implementations.standalone_playwright_rss_article_scraper import (
    StandalonePlaywrightRSSArticleScraper,
)
from src.hex_machina.ingestion.scrapers.implementations.stealth_playwright_rss_article_scraper import (
    StealthPlaywrightRSSArticleScraper,
)

logger = logging.getLogger(__name__)

SCRAPER_CLASS_MAP = {
    "deepmind_google_scraper": DeepMindGoogleScraper,
    "hai_scraper": HAIScraper,
    "hbr_scraper": HBRScraper,
    "meta_scraper": MetaScraper,
    "microsoft_scraper": MicrosoftScraper,
    "playwright_rss_article_scraper": PlaywrightRSSArticleScraper,
    "research_google_scraper": ResearchGoogleScraper,
    "synced_review_scraper": SyncedReviewScraper,
    "stealth_playwright_rss_article_scraper": StealthPlaywrightRSSArticleScraper,
    "scrapy_rss_article_scraper": ScrapyRSSArticleScraper,
    "simple_playwright_rss_article_scraper": SimplePlaywrightRSSArticleScraper,
    "standalone_playwright_rss_article_scraper": StandalonePlaywrightRSSArticleScraper,
    # Add other mappings as needed
}


async def custom_scraping_headers(
    *,
    browser_type_name: str,
    playwright_request: Any,  # playwright.async_api.Request
    scrapy_request_data: dict,
) -> Dict[str, str]:
    """
    Custom header processing function for meaningful scraping headers.

    This function enhances Playwright's default headers with scraping-specific
    headers while maintaining browser-like behavior for better stealth.

    Args:
        browser_type_name: The type of browser (chromium, firefox, webkit)
        playwright_request: The Playwright request object
        scrapy_request_data: Scrapy request data containing method, url, headers, body, encoding

    Returns:
        Dictionary of headers to override
    """
    # Get Playwright's default headers
    headers = await playwright_request.all_headers()

    # Get Scrapy headers
    scrapy_headers = scrapy_request_data["headers"].to_unicode_dict()

    # Enhanced headers for better scraping
    enhanced_headers = {
        # Essential headers for web scraping
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",  # Do Not Track
    }

    # Preserve important Scrapy headers if present (excluding cookies)
    # Note: Cookies are intentionally excluded for clean requests
    if "Referer" in scrapy_headers:
        enhanced_headers["Referer"] = scrapy_headers["Referer"]

    # Add browser-specific headers
    if browser_type_name == "chromium":
        enhanced_headers.update(
            {
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
            }
        )
    elif browser_type_name == "firefox":
        enhanced_headers.update(
            {
                "Sec-Ch-Ua": '"Mozilla";v="5.0", "Firefox";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
            }
        )
    elif browser_type_name == "webkit":
        enhanced_headers.update(
            {
                "Sec-Ch-Ua": '"Safari";v="17.0"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
            }
        )

    # Merge with Playwright's default headers, giving priority to our enhanced headers
    final_headers = {**headers, **enhanced_headers}

    # Log headers for debugging (only in DEBUG mode)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Generated headers for {browser_type_name}: {final_headers}")

    return final_headers


class IngestionRunner:
    """Orchestrates the scraping and storage process for ingestion using Scrapy CrawlerProcess."""

    def __init__(self, config: IngestionConfig, storage_manager, crawler_process=None):
        self.config = config
        self.storage_manager = storage_manager
        self.crawler_process = crawler_process or CrawlerProcess(self._build_settings())
        self._original_signal_handlers = {}

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        if hasattr(self.crawler_process, "stop"):
            self.crawler_process.stop()
        sys.exit(0)

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signals = [signal.SIGINT, signal.SIGTERM]
        for sig in signals:
            self._original_signal_handlers[sig] = signal.signal(
                sig, self._signal_handler
            )

    def _restore_signal_handlers(self):
        """Restore original signal handlers."""
        for sig, handler in self._original_signal_handlers.items():
            signal.signal(sig, handler)

    def _build_settings(self):
        """Build comprehensive Scrapy settings from configuration."""
        settings = get_project_settings()

        # Set all fields from ScrapyConfig with proper naming
        scrapy_config = self.config.scrapy.model_dump()

        # Map config fields to Scrapy settings
        setting_mappings = {
            # Basic Settings
            "user_agent": "USER_AGENT",  # Will be set to None for Playwright
            "robotstxt_obey": "ROBOTSTXT_OBEY",
            # Performance Settings
            "concurrent_requests": "CONCURRENT_REQUESTS",
            "concurrent_requests_per_domain": "CONCURRENT_REQUESTS_PER_DOMAIN",
            "concurrent_requests_per_ip": "CONCURRENT_REQUESTS_PER_IP",
            # Download Settings
            "download_delay": "DOWNLOAD_DELAY",
            "download_timeout": "DOWNLOAD_TIMEOUT",
            "download_maxsize": "DOWNLOAD_MAXSIZE",
            # Retry Settings
            "retry_enabled": "RETRY_ENABLED",
            "retry_times": "RETRY_TIMES",
            "retry_http_codes": "RETRY_HTTP_CODES",
            # Cache Settings
            "httpcache_enabled": "HTTPCACHE_ENABLED",
            "httpcache_expiration_secs": "HTTPCACHE_EXPIRATION_SECS",
            "httpcache_dir": "HTTPCACHE_DIR",
            # Cookie Settings
            "cookies_enabled": "COOKIES_ENABLED",
            # Compression Settings
            "compression_enabled": "COMPRESSION_ENABLED",
            # AutoThrottle Settings
            "autothrottle_enabled": "AUTOTHROTTLE_ENABLED",
            "autothrottle_start_delay": "AUTOTHROTTLE_START_DELAY",
            "autothrottle_max_delay": "AUTOTHROTTLE_MAX_DELAY",
            "autothrottle_target_concurrency": "AUTOTHROTTLE_TARGET_CONCURRENCY",
            # Memory Settings
            "memusage_enabled": "MEMUSAGE_ENABLED",
            "memusage_limit": "MEMUSAGE_LIMIT",
            # Logging Settings
            "log_enabled": "LOG_ENABLED",
            "log_stdout": "LOG_STDOUT",
            # Stats Settings
            "stats_enabled": "STATS_ENABLED",
            # Telnet Settings
            "telnet_console_enabled": "TELNETCONSOLE_ENABLED",
        }

        # Apply mapped settings
        for config_key, setting_key in setting_mappings.items():
            if config_key in scrapy_config and scrapy_config[config_key] is not None:
                # Special handling for user_agent when using Playwright
                if config_key == "user_agent":
                    # Set Scrapy user agent to None to let Playwright use browser default
                    # This prevents conflicts between Scrapy and Playwright user agents
                    settings.set(setting_key, None)
                    logger.info(
                        "Setting Scrapy USER_AGENT to None to let Playwright use browser default"
                    )
                else:
                    settings.set(setting_key, scrapy_config[config_key])

        # Apply custom settings if provided
        if scrapy_config.get("custom_settings"):
            for key, value in scrapy_config["custom_settings"].items():
                settings.set(key.upper(), value)

        # Set log level if present
        if self.config.log_level:
            settings.set("LOG_LEVEL", self.config.log_level)

        # Set ingestion-specific settings
        settings.set("INGESTION_RUN_ID", self._generate_run_id())

        # Set articles limit as Scrapy setting
        if self.config.articles_limit is not None:
            settings.set("CLOSESPIDER_ITEMCOUNT", self.config.articles_limit)
            logger.info(f"Setting Scrapy item limit to: {self.config.articles_limit}")

        # Add domain headers configuration
        if hasattr(self.config, "domain_headers") and self.config.domain_headers:
            settings.set("DOMAIN_HEADERS_CONFIG", self.config.domain_headers)
            logger.info(
                f"Loaded domain-specific headers for {len(self.config.domain_headers)} domains"
            )
        else:
            settings.set("DOMAIN_HEADERS_CONFIG", {})
            logger.info("No domain-specific headers configured, using defaults")

        # Force disable all caching and cookies for fresh content
        settings.set("HTTPCACHE_ENABLED", False)
        settings.set("HTTPCACHE_EXPIRATION_SECS", 0)
        settings.set("HTTPCACHE_DIR", None)
        settings.set("COOKIES_ENABLED", False)
        settings.set("COOKIES_DEBUG", False)
        logger.info("Disabled all caching and cookies for fresh content retrieval")

        # Date threshold will be passed directly to scrapers via scraper_config
        if self.config.date_threshold is not None:
            logger.info(
                f"Date threshold will be passed to scrapers: {self.config.date_threshold}"
            )

        # Always enable Playwright for all scrapers
        settings.set(
            "TWISTED_REACTOR", "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
        )
        settings.set(
            "DOWNLOAD_HANDLERS",
            {
                "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
                "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            },
        )

        # Add settings for proper cleanup and shutdown
        settings.set("CLOSESPIDER_TIMEOUT", 0)  # Close immediately when no more items
        settings.set("CLOSESPIDER_PAGECOUNT", 0)  # Don't close based on page count
        settings.set("CLOSESPIDER_ERRORCOUNT", 0)  # Don't close based on error count
        settings.set("DOWNLOAD_TIMEOUT", 30)  # 30 second timeout for downloads
        settings.set("DOWNLOAD_MAXSIZE", 0)  # No size limit
        settings.set("DOWNLOAD_WARNSIZE", 0)  # No warning size
        settings.set("DOWNLOAD_FAIL_ON_DATALOSS", False)  # Don't fail on data loss

        # Configure Playwright launch options
        default_playwright_options = {
            "headless": True,
            "timeout": 30000,  # 30 seconds timeout for browser launch
            "args": [
                # Security and sandbox args
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                # Performance optimization
                "--no-first-run",
                "--no-zygote",
                "--disable-gpu",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-field-trial-config",
                "--disable-ipc-flooding-protection",
                # Stealth and anti-detection
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-extensions",
                "--disable-plugins",
                "--no-default-browser-check",
                "--disable-default-apps",
                "--disable-sync",
                "--disable-translate",
                "--hide-scrollbars",
                "--mute-audio",
                "--disable-logging",
                "--disable-background-networking",
                "--disable-client-side-phishing-detection",
                "--disable-component-extensions-with-background-pages",
                "--disable-domain-reliability",
                "--disable-features=TranslateUI",
                # Additional stealth args
                "--disable-background-media-suspend",
                "--disable-features=TranslateUI,BlinkGenPropertyTrees",
                "--disable-features=AudioServiceOutOfProcess",
                # Memory optimization
                "--memory-pressure-off",
                "--max_old_space_size=4096",
            ],
            # Additional launch options for better performance and stealth
            "ignore_default_args": ["--enable-automation"],  # Hide automation flag
        }

        # Use configured options if provided, otherwise use defaults
        playwright_options = (
            self.config.scrapy.playwright_launch_options or default_playwright_options
        )
        settings.set("PLAYWRIGHT_LAUNCH_OPTIONS", playwright_options)
        settings.set("PLAYWRIGHT_INCLUDE_PAGE", True)

        # Additional scrapy-playwright settings
        settings.set("PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT", 5000)  # 30 seconds
        settings.set("PLAYWRIGHT_DEFAULT_TIMEOUT", 5000)  # 30 seconds
        settings.set("PLAYWRIGHT_HEADLESS", True)  # Default to headless mode
        settings.set(
            "PLAYWRIGHT_RESTART_DISCONNECTED_BROWSER",
            self.config.scrapy.restart_disconnected_browser,
        )  # Restart browser if disconnected
        # Use custom header processing function for meaningful scraping headers
        settings.set(
            "PLAYWRIGHT_PROCESS_REQUEST_HEADERS",
            custom_scraping_headers,
        )  # Use custom headers for better scraping
        settings.set("PLAYWRIGHT_LAUNCH_OPTIONS", playwright_options)

        # Memory usage extension for Playwright (replaces default Scrapy extension)
        settings.set(
            "EXTENSIONS",
            {
                "scrapy.extensions.memusage.MemoryUsage": None,  # Disable default
                "scrapy_playwright.memusage.ScrapyPlaywrightMemoryUsageExtension": 0,  # Enable Playwright-aware extension
            },
        )

        # Set pipelines and middlewares
        self._configure_pipelines_and_middlewares(settings)

        # Scrapy settings
        settings.set("LOG_LEVEL", "INFO")  # Reduce verbosity
        settings.set("USER_AGENT", self.config.scrapy.user_agent)
        settings.set("DOWNLOAD_DELAY", 1)  # 1 second delay between requests
        settings.set("RANDOMIZE_DOWNLOAD_DELAY", 0.5)  # Randomize delay by ±0.5 seconds
        settings.set("CONCURRENT_REQUESTS", 16)  # Limit concurrent requests
        settings.set("CONCURRENT_REQUESTS_PER_DOMAIN", 8)  # Limit per domain
        settings.set("AUTOTHROTTLE_ENABLED", True)  # Enable auto-throttling
        settings.set("AUTOTHROTTLE_START_DELAY", 1)  # Start with 1 second delay
        settings.set("AUTOTHROTTLE_MAX_DELAY", 60)  # Max 60 seconds delay
        settings.set(
            "AUTOTHROTTLE_TARGET_CONCURRENCY", 1.0
        )  # Target 1 request per second
        settings.set("AUTOTHROTTLE_DEBUG", False)  # Disable debug output

        # HTTP Error Handling - Allow non-200 responses to be processed
        settings.set("HTTPERROR_ALLOWED_CODES", [403, 404, 429, 500, 502, 503, 504])
        settings.set(
            "HTTPERROR_ALLOW_ALL", True
        )  # Allow all status codes to be processed

        # Retry Configuration
        settings.set("RETRY_ENABLED", True)
        settings.set("RETRY_TIMES", 3)  # Retry failed requests 3 times
        settings.set(
            "RETRY_HTTP_CODES", [500, 502, 503, 504, 408, 429]
        )  # Retry on server errors and rate limits
        settings.set("RETRY_PRIORITY_ADJUST", -1)  # Lower priority for retries

        # Download Timeouts
        settings.set("DOWNLOAD_TIMEOUT", 30)  # 30 seconds timeout
        settings.set("DOWNLOAD_MAXSIZE", 0)  # No size limit
        settings.set("DOWNLOAD_WARNSIZE", 0)  # No warning size

        # Cache and Duplicate Filtering
        settings.set("DUPEFILTER_ENABLED", True)
        settings.set("DUPEFILTER_DEBUG", False)
        settings.set("HTTPCACHE_ENABLED", False)  # Disable caching for fresh content
        settings.set("HTTPCACHE_EXPIRATION_SECS", 0)  # No cache expiration
        settings.set("COOKIES_ENABLED", False)  # Disable cookies globally
        settings.set("COOKIES_DEBUG", False)  # Disable cookie debugging

        return settings

    def _configure_pipelines_and_middlewares(self, settings):
        """Configure pipelines and middlewares based on settings."""
        # Item pipelines
        pipelines = {
            "src.hex_machina.ingestion.processing.scrapy_pipelines.ArticleStorePipeline": 100,
        }
        settings.set("ITEM_PIPELINES", pipelines)

        # Downloader middlewares - ordered from closest to engine to closest to downloader
        middlewares = {}

        # Default headers middleware (order 400)
        middlewares[
            "scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware"
        ] = 400

        # Download timeout middleware (order 350)
        middlewares[
            "scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware"
        ] = 350

        # Retry middleware (order 550)
        if self.config.scrapy.retry_enabled:
            middlewares["scrapy.downloadermiddlewares.retry.RetryMiddleware"] = 550

        middlewares["scrapy.downloadermiddlewares.redirect.RedirectMiddleware"] = 600
        middlewares["scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware"] = 750

        # Only add our custom middleware if not already configured
        if (
            "src.hex_machina.ingestion.core.middleware.RedirectLoggingMiddleware"
            not in middlewares
        ):
            middlewares[
                "src.hex_machina.ingestion.core.middleware.RedirectLoggingMiddleware"
            ] = 950  # Log redirects

        # Cookies middleware (order 700) - Disabled for clean requests
        if False and self.config.scrapy.cookies_enabled:  # Force disable cookies
            middlewares["scrapy.downloadermiddlewares.cookies.CookiesMiddleware"] = 700

        # HTTP compression middleware (order 810)
        if self.config.scrapy.compression_enabled:
            middlewares[
                "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware"
            ] = 810

        # HTTP cache middleware (order 900) - Disabled for fresh content
        if False:  # Force disable HTTP cache
            middlewares[
                "scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware"
            ] = 900

        # Downloader stats middleware (order 851)
        middlewares["scrapy.downloadermiddlewares.stats.DownloaderStats"] = 851

        settings.set("DOWNLOADER_MIDDLEWARES", middlewares)

        # Spider middlewares
        spider_middlewares = {}

        settings.set("SPIDER_MIDDLEWARES", spider_middlewares)

    def _generate_run_id(self):
        """Generate a unique run ID for this ingestion session."""
        import uuid
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"ingestion_{timestamp}_{unique_id}"

    def _get_scraper_class(self, scraper_type):
        """Get scraper class by type."""
        return SCRAPER_CLASS_MAP.get(scraper_type)

    def _build_spider_kwargs(self, scraper_cfg):
        """Build keyword arguments for spider initialization."""
        import os

        # Convert relative file paths to absolute file URLs
        processed_urls = []
        for url in scraper_cfg.start_urls:
            if not url.startswith(("http://", "https://", "file://")):
                # It's a relative file path, convert to absolute file URL
                abs_path = os.path.abspath(url)
                file_url = f"file://{abs_path}"
                processed_urls.append(file_url)
                logger.debug(
                    f"Converted relative path '{url}' to file URL '{file_url}'"
                )
            else:
                processed_urls.append(url)

        # Create scraper config with date threshold included
        scraper_config = scraper_cfg.model_dump()
        if self.config.date_threshold is not None:
            scraper_config["date_threshold"] = self.config.date_threshold

        kwargs = {
            "start_urls": processed_urls,
            "scraper_config": scraper_config,
        }

        return kwargs

    def run(self):
        """Run the ingestion process with all configured scrapers."""
        # Set GLOBAL_STORAGE_MANAGER for the pipeline
        import json
        from datetime import datetime

        import src.hex_machina.ingestion.processing.scrapy_pipelines as scrapy_pipelines
        from src.hex_machina.storage.models import IngestionOperationDB

        scrapy_pipelines.GLOBAL_STORAGE_MANAGER = self.storage_manager

        # Create ingestion operation record
        run_id = self._generate_run_id()
        start_time = datetime.now()

        ingestion_op = IngestionOperationDB(
            start_time=start_time,
            end_time=start_time,  # Will be updated later
            num_articles_processed=0,
            num_errors=0,
            status="running",
            parameters=json.dumps(self.config.model_dump()),
        )

        # Save to database to get the integer ID
        saved_op = self.storage_manager.add_ingestion_operation(ingestion_op)
        ingestion_run_id = saved_op.id

        # Set the integer ID in Scrapy settings
        self.crawler_process.settings.set("INGESTION_RUN_ID", ingestion_run_id)

        summary = {
            "crawlers_run": 0,
            "unknown_types": [],
            "errors": [],
            "run_id": run_id,
            "ingestion_run_id": ingestion_run_id,
            "start_time": None,
            "end_time": None,
        }

        logger.info(f"Starting ingestion run: {run_id} (DB ID: {ingestion_run_id})")
        summary["start_time"] = self._get_current_timestamp()

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

        try:
            for scraper_cfg in self.config.scrapers:
                scraper_class = self._get_scraper_class(scraper_cfg.type)
                if not scraper_class:
                    logger.warning(f"Unknown scraper type: {scraper_cfg.type}")
                    summary["unknown_types"].append(scraper_cfg.type)
                    continue

                kwargs = self._build_spider_kwargs(scraper_cfg)
                logger.info(
                    f"Starting scraper: {scraper_cfg.type} with {len(scraper_cfg.start_urls)} URLs"
                )
                self.crawler_process.crawl(scraper_class, **kwargs)
                summary["crawlers_run"] += 1

            if summary["crawlers_run"] > 0:
                self.crawler_process.start()
                # Explicitly stop the crawler process after completion
                self.crawler_process.stop()
            else:
                logger.warning("No valid scrapers to run")

        except Exception as e:
            logger.error(f"Error running crawlers: {e}")
            summary["errors"].append(str(e))
            # Update operation status to failed
            saved_op.status = "failed"
            saved_op.end_time = datetime.now()
            self.storage_manager.update_ingestion_operation(saved_op)
        finally:
            # Restore original signal handlers
            self._restore_signal_handlers()

            summary["end_time"] = self._get_current_timestamp()

            # Count articles and errors for this operation
            num_articles = self.storage_manager.count_articles_for_operation(
                ingestion_run_id
            )
            num_errors = self.storage_manager.count_errors_for_operation(
                ingestion_run_id
            )

            # Update operation with final status and counts
            saved_op.end_time = datetime.now()
            saved_op.status = "completed" if not summary["errors"] else "failed"
            saved_op.num_articles_processed = num_articles
            saved_op.num_errors = num_errors
            self.storage_manager.update_ingestion_operation(saved_op)

            logger.info(
                f"Completed ingestion run: {run_id} (DB ID: {ingestion_run_id}) - "
                f"Articles: {num_articles}, Errors: {num_errors}"
            )

        return summary

    def _get_current_timestamp(self):
        """Get current timestamp for logging."""
        from datetime import datetime

        return datetime.now().isoformat()
