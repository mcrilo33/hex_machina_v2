#!/usr/bin/env python3
"""Compare database access methods to identify the issue."""

import asyncio

from src.hex_machina.enrichment.config.database_config import DatabaseConfigManager
from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import ArticleDB


async def compare_db_access():
    """Compare different database access methods."""

    print("=== Testing Database Access Methods ===\n")

    # Method 1: Direct access with hardcoded path
    print("1. Direct access with hardcoded path:")
    try:
        storage_manager = get_storage_manager("storage/articles14.db")
        with storage_manager.session() as session:
            article = session.query(ArticleDB).filter(ArticleDB.id == 1).first()
            if article:
                print(
                    f"   ✓ Found article: ID {article.id}, Title: {article.title[:30]}..."
                )
            else:
                print("   ✗ No article found")
    except Exception as e:
        print(f"   Error: {e}")

    # Method 2: Access via config manager
    print("\n2. Access via config manager:")
    try:
        database_config_manager = DatabaseConfigManager()
        db_path = database_config_manager.get_db_path()
        print(f"   Config path: {db_path}")

        storage_manager = get_storage_manager(db_path)
        with storage_manager.session() as session:
            article = session.query(ArticleDB).filter(ArticleDB.id == 1).first()
            if article:
                print(
                    f"   ✓ Found article: ID {article.id}, Title: {article.title[:30]}..."
                )
            else:
                print("   ✗ No article found")
    except Exception as e:
        print(f"   Error: {e}")

    # Method 3: Test with different session management
    print("\n3. Test with different session management:")
    try:
        database_config_manager = DatabaseConfigManager()
        db_path = database_config_manager.get_db_path()

        storage_manager = get_storage_manager(db_path)
        session = storage_manager.session()
        try:
            article = session.query(ArticleDB).filter(ArticleDB.id == 1).first()
            if article:
                print(
                    f"   ✓ Found article: ID {article.id}, Title: {article.title[:30]}..."
                )
            else:
                print("   ✗ No article found")
        finally:
            session.close()
    except Exception as e:
        print(f"   Error: {e}")


if __name__ == "__main__":
    asyncio.run(compare_db_access())
