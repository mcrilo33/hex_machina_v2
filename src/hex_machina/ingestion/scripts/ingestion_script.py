"""Main ingestion script for Hex Machina v2."""

import argparse
from pathlib import Path

from src.hex_machina.ingestion.article_models import ArticleModel
from src.hex_machina.ingestion.config_loader import load_ingestion_config
from src.hex_machina.ingestion.ingestion_report_generator import (
    generate_html_ingestion_report,
)
from src.hex_machina.ingestion.ingestion_runner import IngestionRunner
from src.hex_machina.storage.manager import StorageManager
from src.hex_machina.utils.logging_utils import get_logger

# Configure logging
logger = get_logger(__name__)


def convert_articledb_to_articlemodel(article_db) -> ArticleModel:
    """Convert ArticleDB object to ArticleModel object.

    Args:
        article_db: ArticleDB object from storage

    Returns:
        ArticleModel object for reporting
    """
    import json

    # Parse JSON strings back to dictionaries
    article_metadata = {}
    if article_db.article_metadata:
        try:
            article_metadata = json.loads(article_db.article_metadata)
        except (json.JSONDecodeError, TypeError):
            article_metadata = {}

    ingestion_metadata = {}
    if article_db.ingestion_metadata:
        try:
            ingestion_metadata = json.loads(article_db.ingestion_metadata)
        except (json.JSONDecodeError, TypeError):
            ingestion_metadata = {}

    return ArticleModel(
        title=article_db.title,
        url=article_db.url,
        source_url=article_db.source_url,
        url_domain=article_db.url_domain,
        published_date=article_db.published_date,
        html_content=article_db.html_content,
        text_content=article_db.text_content,
        author=article_db.author,
        article_metadata=article_metadata,
        ingestion_error_status=article_db.ingestion_error_status,
        ingestion_error_message=article_db.ingestion_error_message,
        ingestion_metadata=ingestion_metadata,
    )


def main() -> None:
    """CLI entrypoint for the ingestion pipeline."""
    parser = argparse.ArgumentParser(description="Hex Machina Ingestion Script")
    parser.add_argument("--config", required=True, help="Path to config YAML file")
    parser.add_argument(
        "--output-dir", default="reports/", help="Directory to save the report"
    )
    args = parser.parse_args()

    try:
        # Load config using the new config loader
        logger.info(f"Loading configuration from {args.config}")
        config = load_ingestion_config(args.config)
        logger.info(f"Loaded configuration with {len(config.scrapers)} scrapers")

        # Initialize storage manager
        logger.info(f"Initializing storage manager with database: {config.db_path}")
        storage_manager = StorageManager(config.db_path)

        # Run ingestion using the new ingestion runner
        logger.info("Starting ingestion process")
        runner = IngestionRunner(config, storage_manager)
        summary = runner.run()

        logger.info(f"Ingestion completed. Summary: {summary}")

        # Get articles from storage for reporting
        # Note: In a real implementation, you might want to get articles from the storage
        # based on the ingestion run ID or other criteria
        article_dbs = storage_manager.get_articles_for_operation(summary.get("run_id"))

        if not article_dbs:
            logger.warning("No articles found for reporting")
            print(
                "⚠️  No articles found for reporting. This might be normal for the first run."
            )
            return

        # Convert ArticleDB objects to ArticleModel objects for reporting
        articles = [
            convert_articledb_to_articlemodel(article_db) for article_db in article_dbs
        ]
        logger.info(f"Found {len(articles)} articles for reporting")

        # Create output directory if it doesn't exist
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate report using the new report generator
        logger.info("Generating ingestion report")

        # Create a mock operation object for reporting
        import json
        from datetime import datetime

        from src.hex_machina.storage.models import IngestionOperationDB

        # Parse the start and end times from the summary
        start_time = datetime.fromisoformat(summary["start_time"])
        end_time = datetime.fromisoformat(summary["end_time"])

        mock_operation = IngestionOperationDB(
            id=summary.get("ingestion_run_id", 0),
            start_time=start_time,
            end_time=end_time,
            num_articles_processed=len(articles),
            num_errors=len([a for a in articles if a.ingestion_error_status]),
            status="completed" if not summary.get("errors") else "failed",
            parameters=json.dumps(summary),
        )

        report_path = generate_html_ingestion_report(
            op=mock_operation,
            articles=articles,
            output_dir=str(output_dir),
            logger=logger,
        )

        logger.info(f"Report generated at: {report_path}")
        print("✅ Ingestion completed successfully!")
        print(f"📊 Report generated at: {report_path}")
        print(f"📈 Summary: {summary}")
        print(f"📄 Articles processed: {len(articles)}")

    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        print(f"❌ Ingestion failed: {e}")
        raise


if __name__ == "__main__":
    main()
