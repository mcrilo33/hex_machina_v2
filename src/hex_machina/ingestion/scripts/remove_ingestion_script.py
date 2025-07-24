"""Script to remove the last or a specific IngestionOperation and its articles from the DB."""

import argparse

from src.hex_machina.storage.manager import StorageManager
from src.hex_machina.utils.logging_utils import get_logger

logger = get_logger(__name__)


def remove_ingestion_operation(db_path: str, op_id: int = None) -> None:
    """Remove the last or a specific ingestion operation and its articles."""
    sm = StorageManager(db_path)
    if op_id is None:
        # Get the last operation
        ops = sm.list_ingestion_operations()
        if not ops:
            logger.warning("No ingestion operations found in the database.")
            print("No ingestion operations found in the database.")
            return
        op = max(ops, key=lambda o: o.end_time or o.start_time)
        op_id = op.id
        logger.info(f"Deleting last ingestion operation: ID={op_id}")
    else:
        op = sm.get_ingestion_operation(op_id)
        if not op:
            logger.error(f"Ingestion operation with ID={op_id} not found.")
            print(f"Ingestion operation with ID={op_id} not found.")
            return
        logger.info(f"Deleting ingestion operation: ID={op_id}")
    # Delete articles for this operation
    articles = [a for a in sm.list_articles() if a.ingestion_run_id == op_id]
    for article in articles:
        sm.delete_article(article.id)
        logger.info(f"Deleted article ID={article.id}")
    # Delete the operation
    sm.delete_ingestion_operation(op_id)
    logger.info(f"Deleted ingestion operation ID={op_id}")
    print(f"Deleted ingestion operation ID={op_id} and {len(articles)} articles.")


def main():
    parser = argparse.ArgumentParser(
        description="Remove an ingestion operation and its articles from the DB."
    )
    parser.add_argument(
        "--db-path", required=True, help="Path to the DuckDB database file."
    )
    parser.add_argument(
        "--id",
        type=int,
        default=None,
        help="ID of the ingestion operation to delete. If not specified, deletes the last one.",
    )
    args = parser.parse_args()
    try:
        remove_ingestion_operation(args.db_path, args.id)
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
