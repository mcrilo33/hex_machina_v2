"""Main ingestion script for Hex Machina v2."""

import argparse
import json
import logging
import sys
from datetime import datetime
from typing import List, Optional

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from src.hex_machina.storage.duckdb_adapter import DuckDBAdapter
from src.hex_machina.storage.manager import StorageManager
from src.hex_machina.storage.models import IngestionOperation
from src.hex_machina.utils.git_utils import get_git_metadata

from ..utils import DateParser
from .scrapers import PlaywrightRSSArticleScraper, StealthPlaywrightRSSArticleScraper
from .utils import get_global_settings, get_rss_feeds_by_scraper

# Configure logging
logger = logging.getLogger(__name__)


class IngestionRunner:
    """Main ingestion runner that orchestrates the scraping process."""

    def __init__(
        self,
        config_path: str = "config/scraping_config.yaml",
        articles_limit: Optional[int] = None,
        date_threshold: Optional[str] = None,
    ):
        """Initialize the ingestion runner.

        Args:
            config_path: Path to the scraping configuration file
            articles_limit: Override articles limit from config
            date_threshold: Override date threshold from config (YYYY-MM-DD format)
        """
        self.config_path = config_path
        self.articles_limit = articles_limit
        self.date_threshold = date_threshold
        self.scraped_articles: List = []

        # Load configuration
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            # Load global settings
            global_settings = get_global_settings(self.config_path)

            # Override with command line arguments if provided
            if self.articles_limit is None:
                self.articles_limit = global_settings.get("articles_limit", 100)

            if self.date_threshold is None:
                self.date_threshold = global_settings.get(
                    "date_threshold", "2024-01-01"
                )

            # Parse date threshold using DateParser
            self.limit_date = DateParser.parse_date(self.date_threshold)

            # Load DB path from config if present
            self.db_path = global_settings.get("db_path", "data/hex_machina.db")

            # Load RSS feeds by scraper type
            self.feeds_by_scraper = get_rss_feeds_by_scraper(self.config_path)

            logger.info(
                f"Loaded configuration: {self.articles_limit} articles limit, "
                f"date threshold: {self.date_threshold}, db_path: {self.db_path}"
            )

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def run(self, verbose: bool = False) -> List:
        """Run the ingestion process.

        Returns:
            List of scraped articles
        """
        logger.info("Starting ingestion process...")

        # Initialize Scrapy settings
        settings = get_project_settings()
        settings.set("DOWNLOAD_DELAY", 1)  # Be respectful to servers

        # Set Scrapy log level based on verbose flag
        if verbose:
            settings.set("LOG_LEVEL", "DEBUG")
            # Use custom log formatter that truncates long fields
            settings.set(
                "LOG_FORMATTER",
                "hex_machina.ingestion.log_formatter.TruncatingLogFormatter",
            )
            settings.set("LOG_DATEFORMAT", "%Y-%m-%d %H:%M:%S")
            settings.set(
                "LOG_FORMAT", "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
            )
        else:
            settings.set("LOG_LEVEL", "INFO")

        # --- Storage Integration ---
        # Get DB path from config (default if not present)
        adapter = DuckDBAdapter(db_path=self.db_path)
        storage_manager = StorageManager(adapter)
        # Create an IngestionOperation record
        parameters_dict = {
            "articles_limit": self.articles_limit,
            "date_threshold": self.date_threshold,
            "config_path": self.config_path,
            "db_path": self.db_path,
            "git": get_git_metadata(),
        }
        ingestion_op = IngestionOperation(
            start_time=datetime.now(),
            end_time=datetime.now(),  # Will update at end
            num_articles_processed=0,  # Will update at end
            num_errors=0,  # Will update at end
            status="running",
            parameters=json.dumps(parameters_dict),
        )
        ingestion_op = storage_manager.add_ingestion_operation(ingestion_op)
        ingestion_run_id = ingestion_op.id
        # Register ArticleStorePipeline in Scrapy settings
        settings.set(
            "ITEM_PIPELINES",
            {"src.hex_machina.ingestion.pipelines.ArticleStorePipeline": 100},
        )
        settings.set("INGESTION_RUN_ID", ingestion_run_id)
        # Set GLOBAL_STORAGE_MANAGER for the pipeline
        import src.hex_machina.ingestion.pipelines as pipelines

        pipelines.GLOBAL_STORAGE_MANAGER = storage_manager

        # Load scraper-specific settings from config
        from src.hex_machina.ingestion.utils import load_scraping_config

        config = load_scraping_config(self.config_path)
        scraper_settings = config.get("scrapers", {})
        playwright_args = scraper_settings.get("playwright", {}).get(
            "launch_args", ["--allow-file-access-from-files"]
        )
        stealth_playwright_args = scraper_settings.get("stealth_playwright", {}).get(
            "launch_args", ["--allow-file-access-from-files"]
        )

        # Create crawler process
        process = CrawlerProcess(settings)

        try:
            # Process each scraper type
            for scraper_type, urls in self.feeds_by_scraper.items():
                if not urls:
                    logger.info(f"No enabled feeds for scraper type: {scraper_type}")
                    continue

                logger.info(f"Processing {len(urls)} feeds with {scraper_type} scraper")

                # Get appropriate scraper class
                scraper_class = self._get_scraper_class(scraper_type)
                if not scraper_class:
                    logger.warning(f"Unknown scraper type: {scraper_type}")
                    continue

                # Add crawler to process with parameters
                if scraper_type == "playwright":
                    process.crawl(
                        scraper_class,
                        start_urls=urls,
                        processed_limit=self.articles_limit,
                        limit_date=self.limit_date,
                        launch_args=playwright_args,
                    )
                elif scraper_type == "stealth_playwright":
                    process.crawl(
                        scraper_class,
                        start_urls=urls,
                        processed_limit=self.articles_limit,
                        limit_date=self.limit_date,
                        launch_args=stealth_playwright_args,
                    )
                else:
                    process.crawl(
                        scraper_class,
                        start_urls=urls,
                        processed_limit=self.articles_limit,
                        limit_date=self.limit_date,
                    )

            # Start the crawling process
            process.start()

            logger.info("Ingestion process completed successfully")
            # For now, return empty list since articles are logged by scrapers
            # TODO: Implement proper item pipeline to collect articles
            # --- Update IngestionOperation at end ---
            from sqlalchemy import and_

            from src.hex_machina.storage.models import Article

            # Count articles and errors for this run
            with adapter.SessionLocal() as session:
                num_articles = (
                    session.query(Article)
                    .filter_by(ingestion_run_id=ingestion_run_id)
                    .count()
                )
                num_errors = (
                    session.query(Article)
                    .filter(
                        and_(
                            Article.ingestion_run_id == ingestion_run_id,
                            Article.ingestion_error_status != None,
                        )
                    )
                    .count()
                )
            # Determine status
            if num_articles == 0:
                status = "failed"
            elif num_errors == 0:
                status = "success"
            elif num_errors < num_articles:
                status = "partial"
            else:
                status = "failed"
            # Update the record
            ingestion_op.end_time = datetime.now()
            ingestion_op.num_articles_processed = num_articles
            ingestion_op.num_errors = num_errors
            ingestion_op.status = status
            storage_manager.update_ingestion_operation(ingestion_op)
            return []

        except Exception as e:
            logger.error(f"Error during ingestion: {e}")
            raise
        finally:
            # Clean up
            process.stop()

    def _get_scraper_class(self, scraper_type: str):
        """Get the appropriate scraper class based on type.

        Args:
            scraper_type: Type of scraper ('playwright' or 'stealth_playwright')

        Returns:
            Scraper class or None if unknown type
        """
        scraper_map = {
            "playwright": PlaywrightRSSArticleScraper,
            "stealth_playwright": StealthPlaywrightRSSArticleScraper,
        }

        return scraper_map.get(scraper_type)


def main():
    """Main entry point for the ingestion script."""
    parser = argparse.ArgumentParser(description="Hex Machina v2 Ingestion Script")
    parser.add_argument(
        "--config",
        default="config/scraping_config.yaml",
        help="Path to scraping configuration file",
    )
    parser.add_argument(
        "--articles-limit",
        type=int,
        help="Maximum number of articles to process (overrides config)",
    )
    parser.add_argument(
        "--date-threshold",
        help="Date threshold in YYYY-MM-DD format (overrides config)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set logging level for Scrapy and other components
    if args.verbose:
        logging.getLogger("scrapy").setLevel(logging.DEBUG)
        logging.getLogger("playwright").setLevel(logging.DEBUG)
        logging.getLogger("asyncio").setLevel(logging.DEBUG)
        logging.getLogger("__main__").setLevel(logging.DEBUG)

    else:
        logging.getLogger("scrapy").setLevel(logging.INFO)
        logging.getLogger("playwright").setLevel(logging.INFO)
        logging.getLogger("asyncio").setLevel(logging.INFO)
        logging.getLogger("__main__").setLevel(logging.INFO)

    try:
        # Create and run ingestion
        runner = IngestionRunner(
            config_path=args.config,
            articles_limit=args.articles_limit,
            date_threshold=args.date_threshold,
        )

        runner.run(verbose=args.verbose)

    except Exception as e:
        logger.error(f"Failed to run ingestion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
