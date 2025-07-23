from typing import List, Optional

from .adapter import BaseDBAdapter
from .models import ArticleDB, IngestionOperationDB


class StorageManager:
    """Main interface for storage operations, delegating to a single DB adapter.

    Args:
        adapter (BaseDBAdapter): The database adapter to use (e.g., DuckDBAdapter).
    """

    def __init__(self, adapter: BaseDBAdapter) -> None:
        self._adapter = adapter

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
