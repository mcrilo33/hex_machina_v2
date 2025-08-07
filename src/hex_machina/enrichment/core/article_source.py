"""Article source resolution for enrichment tasks."""

import json
import logging
from typing import Dict, List, Optional, Union

from src.hex_machina.enrichment.config.database_config import DatabaseConfigManager
from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import ArticleDB


class ArticleSource:
    """Resolves different article sources to ArticleDB objects."""

    def __init__(self):
        self._logger = logging.getLogger("enrichment.core.article_source")
        self._database_config_manager = DatabaseConfigManager()
        self._db_path = self._database_config_manager.get_db_path()
        self._storage_manager = get_storage_manager(self._db_path)

    def resolve_single_article(self, article_id: int) -> Optional[ArticleDB]:
        """Resolve a single article by ID."""
        self._logger.debug(f"Resolving single article ID: {article_id}")

        with self._storage_manager.session() as session:
            article = (
                session.query(ArticleDB).filter(ArticleDB.id == article_id).first()
            )

            if article:
                self._logger.debug(f"Found article: {article.title}")
                return article
            else:
                self._logger.warning(f"Article ID {article_id} not found")
                return None

    def resolve_multiple_articles(self, article_ids: List[int]) -> List[ArticleDB]:
        """Resolve multiple articles by IDs."""
        self._logger.debug(f"Resolving multiple article IDs: {article_ids}")

        with self._storage_manager.session() as session:
            articles = (
                session.query(ArticleDB).filter(ArticleDB.id.in_(article_ids)).all()
            )

            found_ids = [article.id for article in articles]
            missing_ids = set(article_ids) - set(found_ids)

            if missing_ids:
                self._logger.warning(f"Missing article IDs: {missing_ids}")

            self._logger.debug(f"Found {len(articles)} articles")
            return articles

    def resolve_ingestion_operation(self, operation_id: int) -> List[ArticleDB]:
        """Resolve all articles from a specific ingestion operation."""
        self._logger.debug(
            f"Resolving articles for ingestion operation ID: {operation_id}"
        )

        with self._storage_manager.session() as session:
            # Assuming there's a relationship between articles and ingestion operations
            # This might need to be adjusted based on your actual database schema
            articles = (
                session.query(ArticleDB)
                .filter(ArticleDB.ingestion_operation_id == operation_id)
                .all()
            )

            self._logger.debug(
                f"Found {len(articles)} articles for operation {operation_id}"
            )
            return articles

    def resolve_dataset(self, dataset_name: str) -> List[ArticleDB]:
        """Resolve articles from a predefined dataset."""
        self._logger.debug(f"Resolving articles for dataset: {dataset_name}")

        # This is a placeholder - you'll need to implement dataset logic
        # For now, we'll look for articles with specific metadata or tags
        with self._storage_manager.session() as session:
            # Example: look for articles with dataset tag in metadata
            # This needs to be implemented based on your dataset structure
            articles = (
                session.query(ArticleDB)
                .filter(
                    ArticleDB.ingestion_metadata.contains({"dataset": dataset_name})
                )
                .all()
            )

            self._logger.debug(
                f"Found {len(articles)} articles for dataset {dataset_name}"
            )
            return articles

    def resolve_all_articles(self, limit: Optional[int] = None) -> List[ArticleDB]:
        """Resolve all articles in the database."""
        self._logger.debug(f"Resolving all articles (limit: {limit})")

        with self._storage_manager.session() as session:
            query = session.query(ArticleDB)

            if limit:
                query = query.limit(limit)

            articles = query.all()

            self._logger.debug(f"Found {len(articles)} articles")
            return articles

    def resolve_input_file(self, file_path: str) -> Dict:
        """Resolve article data from input file (for non-DB articles)."""
        self._logger.debug(f"Resolving article from input file: {file_path}")

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            self._logger.debug("Loaded article data from file")
            return data

        except Exception as e:
            self._logger.error(f"Error loading input file {file_path}: {e}")
            raise

    def get_article_count(
        self, source_type: str, source_value: Union[int, str, List[int]]
    ) -> int:
        """Get the count of articles for a given source."""
        try:
            if source_type == "single_article":
                return 1 if self.resolve_single_article(source_value) else 0
            elif source_type == "multiple_articles":
                return len(self.resolve_multiple_articles(source_value))
            elif source_type == "ingestion_operation":
                return len(self.resolve_ingestion_operation(source_value))
            elif source_type == "dataset":
                return len(self.resolve_dataset(source_value))
            elif source_type == "all_articles":
                return len(self.resolve_all_articles(source_value))
            else:
                return 0
        except Exception as e:
            self._logger.error(f"Error getting article count: {e}")
            return 0

    def validate_source(
        self, source_type: str, source_value: Union[int, str, List[int]]
    ) -> bool:
        """Validate that a source exists and has articles."""
        count = self.get_article_count(source_type, source_value)
        return count > 0
