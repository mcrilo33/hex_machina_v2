"""Storage module for Hex Machina."""

from .adapter import BaseDBAdapter
from .article_view import ArticleView
from .base import Base
from .duckdb_adapter import DuckDBAdapter
from .manager import StorageManager, get_storage_manager
from .models import (
    ArticleDB,
    EnrichmentDB,
    IngestionOperationDB,
)

__all__ = [
    "Base",
    "BaseDBAdapter",
    "DuckDBAdapter",
    "StorageManager",
    "get_storage_manager",
    "ArticleDB",
    "EnrichmentDB",
    "IngestionOperationDB",
    "ArticleView",
]
