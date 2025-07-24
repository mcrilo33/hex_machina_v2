from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from src.hex_machina.ingestion.config_models import IngestionConfig
from src.hex_machina.ingestion.scrapers import (
    PlaywrightRSSArticleScraper,
    StealthPlaywrightRSSArticleScraper,
    # Add other scrapers as needed
)
from src.hex_machina.utils.logging_utils import get_logger

logger = get_logger(__name__)

SCRAPER_CLASS_MAP = {
    "playwright_rss_article_scraper": PlaywrightRSSArticleScraper,
    "stealth_playwright_rss_article_scraper": StealthPlaywrightRSSArticleScraper,
    # Add other mappings as needed
}


class IngestionRunner:
    """Orchestrates the scraping and storage process for ingestion using Scrapy CrawlerProcess."""

    def __init__(self, config: IngestionConfig, storage_manager, crawler_process=None):
        self.config = config
        self.storage_manager = storage_manager
        self.crawler_process = crawler_process or CrawlerProcess(self._build_settings())

    def _build_settings(self):
        """Build comprehensive Scrapy settings from configuration."""
        settings = get_project_settings()

        # Set all fields from ScrapyConfig with proper naming
        scrapy_config = self.config.scrapy.model_dump()

        # Map config fields to Scrapy settings
        setting_mappings = {
            # Basic Settings
            "user_agent": "USER_AGENT",
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

        # Set articles limit and date threshold as Scrapy settings
        if self.config.articles_limit is not None:
            settings.set("CLOSESPIDER_ITEMCOUNT", self.config.articles_limit)
            logger.info(f"Setting Scrapy item limit to: {self.config.articles_limit}")

        if self.config.date_threshold is not None:
            settings.set("INGESTION_DATE_THRESHOLD", self.config.date_threshold)
            logger.info(
                f"Setting ingestion date threshold to: {self.config.date_threshold}"
            )

        # Set pipelines and middlewares
        self._configure_pipelines_and_middlewares(settings)

        return settings

    def _configure_pipelines_and_middlewares(self, settings):
        """Configure pipelines and middlewares based on settings."""
        # Item pipelines
        pipelines = {
            "src.hex_machina.ingestion.scrapy_pipelines.ArticleStorePipeline": 100,
        }
        settings.set("ITEM_PIPELINES", pipelines)

        # Downloader middlewares - ordered from closest to engine to closest to downloader
        middlewares = {}

        # Default headers middleware (order 400)
        middlewares[
            "scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware"
        ] = 400

        # Random user agent middleware (order 400)
        middlewares["scrapy_user_agents.middlewares.RandomUserAgentMiddleware"] = 400

        # Download timeout middleware (order 350)
        middlewares[
            "scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware"
        ] = 350

        # Retry middleware (order 550)
        if self.config.scrapy.retry_enabled:
            middlewares["scrapy.downloadermiddlewares.retry.RetryMiddleware"] = 550

        # Cookies middleware (order 700)
        if self.config.scrapy.cookies_enabled:
            middlewares["scrapy.downloadermiddlewares.cookies.CookiesMiddleware"] = 700

        # HTTP compression middleware (order 810)
        if self.config.scrapy.compression_enabled:
            middlewares[
                "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware"
            ] = 810

        # HTTP cache middleware (order 900)
        if self.config.scrapy.httpcache_enabled:
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

        kwargs = {
            "start_urls": processed_urls,
            "scraper_config": scraper_cfg.model_dump(),
        }

        return kwargs

    def run(self):
        """Run the ingestion process with all configured scrapers."""
        # Set GLOBAL_STORAGE_MANAGER for the pipeline
        import json
        from datetime import datetime

        import src.hex_machina.ingestion.scrapy_pipelines as scrapy_pipelines
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
