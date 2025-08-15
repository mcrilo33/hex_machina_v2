"""
Cache utilities for LangChain runnables.

This module provides SQLite caching for caching LLM responses
and other runnable outputs to improve performance and reduce API costs.
"""

import logging
from pathlib import Path
from typing import Optional

from langchain.globals import set_llm_cache
from langchain_community.cache import InMemoryCache, SQLiteCache


def setup_sqlite_cache(
    database_path: str = ".langchain.db",
    cache_dir: Optional[str] = None,
) -> None:
    """Set up SQLite cache for LangChain.

    Args:
        database_path: Name of the SQLite database file
        cache_dir: Directory to store the cache file (default: storage directory)

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    # Determine cache directory
    if cache_dir is None:
        # Default to storage directory (3 levels up from langchain_tasks, then into storage)
        cache_dir = Path(__file__).parent.parent.parent.parent / "storage"
    else:
        cache_dir = Path(cache_dir)

    # Ensure cache directory exists
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Full path to cache database
    cache_db_path = cache_dir / database_path

    try:
        # Create SQLite cache (TTL not supported in this version)
        cache = SQLiteCache(database_path=str(cache_db_path))

        # Set as global cache
        set_llm_cache(cache)

        logger.info(f"SQLite cache initialized at {cache_db_path}")

    except Exception as e:
        logger.error(f"Failed to initialize SQLite cache: {e}")
        # Fallback to in-memory cache if SQLite fails
        set_llm_cache(InMemoryCache())
        logger.warning("Falling back to in-memory cache")


def setup_default_cache() -> None:
    """Set up default caching configuration for the project.

    Uses SQLite cache in the storage directory.
    """
    setup_sqlite_cache(
        database_path=".langchain.db",
        cache_dir=None,  # Will use storage directory
    )


def clear_cache(
    database_path: str = ".langchain.db", cache_dir: Optional[str] = None
) -> None:
    """Clear the SQLite cache database.

    Args:
        database_path: Name of the SQLite database file
        cache_dir: Directory containing the cache file

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    # Determine cache directory
    if cache_dir is None:
        cache_dir = Path(__file__).parent.parent.parent.parent / "storage"
    else:
        cache_dir = Path(cache_dir)

    cache_db_path = cache_dir / database_path

    if cache_db_path.exists():
        try:
            cache_db_path.unlink()
            logger.info(f"Cache cleared: {cache_db_path}")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    else:
        logger.info("No cache file found to clear")


def get_cache_info(
    database_path: str = ".langchain.db", cache_dir: Optional[str] = None
) -> dict:
    """Get information about the current cache.

    Args:
        database_path: Name of the SQLite database file
        cache_dir: Directory containing the cache file

    Returns:
        Dictionary with cache information
    """
    import sqlite3

    # Determine cache directory
    if cache_dir is None:
        cache_dir = Path(__file__).parent.parent.parent.parent / "storage"
    else:
        cache_dir = Path(cache_dir)

    cache_db_path = cache_dir / database_path

    if not cache_db_path.exists():
        return {"status": "not_found", "path": str(cache_db_path)}

    try:
        # Connect to SQLite database
        conn = sqlite3.connect(str(cache_db_path))
        cursor = conn.cursor()

        # Get table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        # Get cache entry count from the actual table names
        cache_count = 0
        if tables:
            # Check both possible table names
            for table_name in ["full_llm_cache", "full_md5_llm_cache"]:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                    result = cursor.fetchone()
                    if result:
                        cache_count += result[0]
                except sqlite3.OperationalError:
                    # Table doesn't exist, continue
                    pass

        # Get database size
        cache_size = cache_db_path.stat().st_size if cache_db_path.exists() else 0

        conn.close()

        return {
            "status": "active",
            "path": str(cache_db_path),
            "tables": [table[0] for table in tables],
            "cache_entries": cache_count,
            "size_bytes": cache_size,
            "size_mb": round(cache_size / (1024 * 1024), 2),
        }

    except Exception as e:
        return {"status": "error", "path": str(cache_db_path), "error": str(e)}
