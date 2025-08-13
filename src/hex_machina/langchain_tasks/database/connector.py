"""Simple DuckDB connector for LangChain runnables."""

from typing import Any, Dict, List

import duckdb


class DatabaseConnector:
    """Simple DuckDB connector for database operations."""

    def __init__(self, db_path: str):
        """Initialize with database path.

        Args:
            db_path: Relative or absolute path to DuckDB database file
        """
        self.db_path = db_path
        self._connection = None

    def get_connection(self):
        """Get DuckDB connection."""
        if self._connection is None:
            self._connection = duckdb.connect(self.db_path)
        return self._connection

    def execute_query(
        self, query: str, params: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dicts.

        Args:
            query: SQL query string
            params: Optional parameters for the query

        Returns:
            List of dictionaries representing query results
        """
        conn = self.get_connection()
        if params:
            # Convert dict to list for DuckDB's ? placeholders
            param_values = list(params.values())
            result = conn.execute(query, param_values)
        else:
            result = conn.execute(query)

        # Convert to list of dicts
        columns = result.description
        rows = result.fetchall()

        return [dict(zip([col[0] for col in columns], row)) for row in rows]

    def save_enrichment(
        self, article_id: int, content: str, enrichment_type: str
    ) -> bool:
        """Save an enrichment to the database.

        Args:
            article_id: ID of the article
            content: Enrichment content (JSON string)
            enrichment_type: Type of enrichment

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create enrichments table if it doesn't exist
            create_table_query = """
            CREATE TABLE IF NOT EXISTS enrichments (
                id INTEGER PRIMARY KEY,
                article_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                enrichment_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            self.execute_query(create_table_query)

            # Insert the enrichment
            insert_query = """
            INSERT INTO enrichments (article_id, content, enrichment_type)
            VALUES (?, ?, ?)
            """
            self.execute_query(
                insert_query,
                {
                    "article_id": article_id,
                    "content": content,
                    "enrichment_type": enrichment_type,
                },
            )

            return True
        except Exception as e:
            print(f"Error saving enrichment: {e}")
            return False

    def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
