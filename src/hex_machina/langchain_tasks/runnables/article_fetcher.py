"""ArticleFetcher runnable for fetching articles from database."""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.runnables import Runnable
from langsmith import traceable

from ..database.connector import DatabaseConnector


class ArticleFetcher(Runnable):
    """LangChain runnable that fetches articles from DuckDB."""

    def __init__(self, db_path: str, filters: Dict[str, Any]):
        """Initialize ArticleFetcher.

        Args:
            db_path: Path to DuckDB database
            filters: Dictionary of filters to apply (domain, date_range, limit, etc.)
        """
        self.db_connector = DatabaseConnector(db_path)
        self.filters = filters
        self._logger = logging.getLogger("runnable.ArticleFetcher")

    @traceable(name="ArticleFetcher", run_type="tool")
    def invoke(
        self, inputs: Dict[str, Any], config: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch articles based on configured filters.

        Args:
            inputs: Input dictionary (unused for this runnable)

        Returns:
            List of article dictionaries
        """
        try:
            # Build query based on filters
            query, params = self._build_query()

            # Execute query
            articles = self.db_connector.execute_query(query, params)

            self._logger.info(
                f"Fetched {len(articles)} articles with filters: {self.filters}"
            )
            return articles

        except Exception as e:
            self._logger.error(f"Failed to fetch articles: {e}")
            raise

    def _build_query(self) -> tuple[str, Dict[str, Any]]:
        """Build SQL query based on filters.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        base_query = "SELECT id, title, url, text_content, published_date, author FROM articles WHERE 1=1"
        params = {}

        # Add domain filter
        if "domain" in self.filters:
            base_query += " AND url_domain = ?"
            params["domain"] = self.filters["domain"]

        # Add date range filter
        if "date_range" in self.filters:
            if self.filters["date_range"] == "last_7_days":
                base_query += " AND published_date >= date_trunc('day', now() - interval '7 days')"
            elif self.filters["date_range"] == "last_30_days":
                base_query += " AND published_date >= date_trunc('day', now() - interval '30 days')"

        # Add limit
        limit = self.filters.get("limit", 100)
        base_query += f" LIMIT {limit}"

        return base_query, params

    def __del__(self):
        """Cleanup database connection."""
        if hasattr(self, "db_connector"):
            self.db_connector.close()
