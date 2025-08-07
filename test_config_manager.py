#!/usr/bin/env python3
"""Test the database configuration manager directly."""

import asyncio

from src.hex_machina.enrichment.config.database_config import database_config_manager
from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import ArticleDB


async def test_config_manager():
    """Test the database configuration manager."""

    print("=== Testing Database Configuration Manager ===\n")

    # Test config manager
    print("1. Testing config manager:")
    try:
        db_path = database_config_manager.get_db_path()
        print(f"   Database path: {db_path}")

        enable_by_default = database_config_manager.get_enable_by_default()
        print(f"   Enable by default: {enable_by_default}")

        batch_size = database_config_manager.get_batch_size()
        print(f"   Batch size: {batch_size}")

        max_concurrent = database_config_manager.get_max_concurrent()
        print(f"   Max concurrent: {max_concurrent}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test database access using config manager
    print("\n2. Testing database access using config manager:")
    try:
        db_path = database_config_manager.get_db_path()
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


if __name__ == "__main__":
    asyncio.run(test_config_manager())
