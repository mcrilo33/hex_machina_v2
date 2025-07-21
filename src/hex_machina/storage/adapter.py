from abc import ABC, abstractmethod
from typing import List, Optional

from .models import Article, IngestionOperation


class BaseDBAdapter(ABC):
    """Abstract base class for database adapters.

    Defines the required CRUD operations for Article and IngestionOperation tables.
    All methods return SQLAlchemy ORM objects.
    """

    # --- IngestionOperation CRUD ---

    @abstractmethod
    def add_ingestion_operation(
        self, ingestion_op: IngestionOperation
    ) -> IngestionOperation:
        """Add a new ingestion operation to the database.

        Args:
            ingestion_op (IngestionOperation): The ingestion operation to add.

        Returns:
            IngestionOperation: The added ORM object (with ID assigned).
        """
        pass

    @abstractmethod
    def get_ingestion_operation(self, op_id: int) -> Optional[IngestionOperation]:
        """Retrieve an ingestion operation by its ID.

        Args:
            op_id (int): The ID of the ingestion operation.

        Returns:
            Optional[IngestionOperation]: The ORM object if found, else None.
        """
        pass

    @abstractmethod
    def update_ingestion_operation(
        self, ingestion_op: IngestionOperation
    ) -> IngestionOperation:
        """Update an existing ingestion operation in the database.

        Args:
            ingestion_op (IngestionOperation): The ingestion operation to update.

        Returns:
            IngestionOperation: The updated ORM object.
        """
        pass

    @abstractmethod
    def delete_ingestion_operation(self, op_id: int) -> None:
        """Delete an ingestion operation by its ID.

        Args:
            op_id (int): The ID of the ingestion operation to delete.
        """
        pass

    # --- Article CRUD ---

    @abstractmethod
    def add_article(self, article: Article) -> Article:
        """Add a new article to the database.

        Args:
            article (Article): The article to add.

        Returns:
            Article: The added ORM object (with ID assigned).
        """
        pass

    @abstractmethod
    def get_article(self, article_id: int) -> Optional[Article]:
        """Retrieve an article by its ID.

        Args:
            article_id (int): The ID of the article.

        Returns:
            Optional[Article]: The ORM object if found, else None.
        """
        pass

    @abstractmethod
    def update_article(self, article: Article) -> Article:
        """Update an existing article in the database.

        Args:
            article (Article): The article to update.

        Returns:
            Article: The updated ORM object.
        """
        pass

    @abstractmethod
    def delete_article(self, article_id: int) -> None:
        """Delete an article by its ID.

        Args:
            article_id (int): The ID of the article to delete.
        """
        pass

    @abstractmethod
    def list_articles(self) -> List[Article]:
        """List all articles in the database.

        Returns:
            List[Article]: List of all article ORM objects.
        """
        pass

    @abstractmethod
    def list_ingestion_operations(self) -> List[IngestionOperation]:
        """List all ingestion operations in the database.

        Returns:
            List[IngestionOperation]: List of all ingestion operation ORM objects.
        """
        pass

    @abstractmethod
    def get_article_by_domain_and_title(
        self, url_domain: str, title: str
    ) -> Optional[Article]:
        """Retrieve an article by its url_domain and title.

        Args:
            url_domain (str): The domain of the article URL.
            title (str): The title of the article.

        Returns:
            Optional[Article]: The ORM object if found, else None.
        """
        pass
