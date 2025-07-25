import json
from datetime import datetime
from typing import Any

from src.hex_machina.ingestion.article_models import ArticleModel
from src.hex_machina.storage.manager import StorageManager
from src.hex_machina.storage.models import ArticleDB

GLOBAL_STORAGE_MANAGER = None


class ArticleStorePipeline:
    """Scrapy Item Pipeline to store Article items in the database using StorageManager.

    Args:
        storage_manager (StorageManager): The storage manager instance.
        ingestion_run_id (int): The ID of the current ingestion operation.
    """

    @classmethod
    def from_crawler(cls, crawler):
        from src.hex_machina.ingestion.scrapy_pipelines import GLOBAL_STORAGE_MANAGER

        ingestion_run_id = crawler.settings.get("INGESTION_RUN_ID")
        if GLOBAL_STORAGE_MANAGER is None or ingestion_run_id is None:
            raise ValueError(
                "GLOBAL_STORAGE_MANAGER and INGESTION_RUN_ID must be set before starting"
            )
        return cls(GLOBAL_STORAGE_MANAGER, ingestion_run_id)

    def __init__(self, storage_manager: StorageManager, ingestion_run_id: int) -> None:
        self.storage_manager = storage_manager
        self.ingestion_run_id = ingestion_run_id

    def _validate_content_lengths(self, item: ArticleModel) -> tuple[str, str]:
        """Validate content lengths and return appropriate error status and message.

        Args:
            item: The article item to validate

        Returns:
            Tuple of (error_status, error_message)
        """
        html_length = len(item.html_content) if item.html_content else 0
        text_length = len(item.text_content) if item.text_content else 0

        # Check if there's already an error
        if item.ingestion_error_status:
            return item.ingestion_error_status, item.ingestion_error_message or ""

        # Validate HTML content length
        if html_length < 10000:
            return (
                "HTML_TOO_SHORT",
                f"HTML content too short: {html_length} characters (minimum: 10000)",
            )

        # Validate text content length
        if text_length < 465:
            return (
                "TEXT_TOO_SHORT",
                f"Text content too short: {text_length} characters (minimum: 465)",
            )

        # No errors
        return None, ""

    def process_item(self, item: Any, spider: Any) -> Any:
        """Process each Article item and store it in the database, checking for existence.

        Args:
            item (Any): The item scraped (should be Article).
            spider (Any): The spider instance (unused).

        Returns:
            Any: The processed item.
        """
        if not isinstance(item, ArticleModel):
            item = ArticleModel(**item)

        # Check for existence by url_domain and title
        existing = self.storage_manager._adapter.get_article_by_domain_and_title(
            item.url_domain, item.title
        )
        if existing:
            # Optionally, update the existing article instead of skipping
            # self.storage_manager.update_article(existing)
            return item  # Skip insertion if already exists

        # Validate content lengths and update error status
        error_status, error_message = self._validate_content_lengths(item)

        # Ensure ingestion_metadata includes the scraper name
        ingestion_metadata = (
            dict(item.ingestion_metadata) if item.ingestion_metadata else {}
        )
        if hasattr(spider, "name"):
            ingestion_metadata["scraper_name"] = spider.name

        # Convert to Article ORM model
        article = ArticleDB(
            title=item.title,
            url=item.url,
            source_url=item.source_url,
            url_domain=item.url_domain,
            published_date=item.published_date,
            html_content=item.html_content,
            text_content=item.text_content,
            author=item.author,
            article_metadata=json.dumps(item.article_metadata),
            ingestion_metadata=json.dumps(ingestion_metadata),
            ingestion_run_id=self.ingestion_run_id,
            ingested_at=datetime.now(),
            ingestion_error_status=error_status,
            ingestion_error_message=error_message,
        )
        # Store in DB
        self.storage_manager.add_article(article)
        return item
