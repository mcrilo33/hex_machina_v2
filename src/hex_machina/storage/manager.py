from typing import List, Optional

from src.hex_machina.storage.duckdb_adapter import DuckDBAdapter
from src.hex_machina.storage.models import ArticleDB, IngestionOperationDB


class StorageManager:
    """Main interface for storage operations, delegating to a single DB adapter.

    Args:
        db_path (str): Path to the database file.
    """

    def __init__(self, db_path: str) -> None:
        self._adapter = DuckDBAdapter(db_path)

    # --- IngestionOperation CRUD ---

    def add_ingestion_operation(
        self, ingestion_op: IngestionOperationDB
    ) -> IngestionOperationDB:
        """Add a new ingestion operation to the database."""
        return self._adapter.add_ingestion_operation(ingestion_op)

    def get_ingestion_operation(self, op_id: int) -> Optional[IngestionOperationDB]:
        """Retrieve an ingestion operation by its ID."""
        return self._adapter.get_ingestion_operation(op_id)

    def update_ingestion_operation(
        self, ingestion_op: IngestionOperationDB
    ) -> IngestionOperationDB:
        """Update an existing ingestion operation in the database."""
        return self._adapter.update_ingestion_operation(ingestion_op)

    def delete_ingestion_operation(self, op_id: int) -> None:
        """Delete an ingestion operation by its ID."""
        self._adapter.delete_ingestion_operation(op_id)

    def list_ingestion_operations(self) -> List[IngestionOperationDB]:
        """List all ingestion operations in the database."""
        return self._adapter.list_ingestion_operations()

    # --- Article CRUD ---

    def add_article(self, article: ArticleDB) -> ArticleDB:
        """Add a new article to the database."""
        return self._adapter.add_article(article)

    def get_article(self, article_id: int) -> Optional[ArticleDB]:
        """Retrieve an article by its ID."""
        return self._adapter.get_article(article_id)

    def update_article(self, article: ArticleDB) -> ArticleDB:
        """Update an existing article in the database."""
        return self._adapter.update_article(article)

    def delete_article(self, article_id: int) -> None:
        """Delete an article by its ID."""
        self._adapter.delete_article(article_id)

    def list_articles(self) -> List[ArticleDB]:
        """List all articles in the database."""
        return self._adapter.list_articles()

    def get_articles_for_operation(
        self, run_id: Optional[str] = None
    ) -> List[ArticleDB]:
        """Get articles for a specific operation or all articles if no run_id provided.

        Args:
            run_id: Optional run ID to filter articles by operation

        Returns:
            List of articles
        """
        if run_id:
            # For now, return all articles since we don't have operation filtering yet
            # In a real implementation, you'd filter by the run_id
            return self.list_articles()
        else:
            return self.list_articles()

    def count_articles_for_operation(self, ingestion_run_id: int) -> int:
        """Count the number of articles processed for a specific ingestion operation.

        Args:
            ingestion_run_id (int): The ID of the ingestion operation.

        Returns:
            int: The number of articles processed.
        """
        return self._adapter.count_articles_for_operation(ingestion_run_id)

    def count_errors_for_operation(self, ingestion_run_id: int) -> int:
        """Count the number of articles with errors for a specific ingestion operation.

        Args:
            ingestion_run_id (int): The ID of the ingestion operation.

        Returns:
            int: The number of articles with errors.
        """
        return self._adapter.count_errors_for_operation(ingestion_run_id)
