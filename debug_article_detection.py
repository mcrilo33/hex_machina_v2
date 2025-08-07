#!/usr/bin/env python3
"""Debug script to test article detection and database saving."""

import asyncio
import json

from src.hex_machina.enrichment.tasks.runner import task_runner
from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import ArticleDB


async def debug_article_detection():
    """Debug article detection and database saving."""

    # Load test data
    with open("test_db_article_input.json", "r") as f:
        input_data = json.load(f)

    print("Input data keys:", list(input_data.keys()))
    print("Input data ID:", input_data.get("id"))

    # Test direct database lookup
    print("\nTesting direct database lookup...")
    try:
        from src.hex_machina.enrichment.config.database_config import (
            DatabaseConfigManager,
        )

        database_config_manager = DatabaseConfigManager()
        db_path = database_config_manager.get_db_path()
        print(f"Using database path: {db_path}")

        storage_manager = get_storage_manager(db_path)
        with storage_manager.session() as session:
            article = session.query(ArticleDB).filter(ArticleDB.id == 1).first()
            if article:
                print(f"✓ Found article in database: ID {article.id}")
                print(f"  Title: {article.title}")
                print(f"  URL: {article.url}")
                print(f"  Domain: {article.url_domain}")
            else:
                print("✗ Article not found in database")
    except Exception as e:
        print(f"Error accessing database: {e}")

    # Test article detection
    print("\nTesting article detection...")
    article_context = task_runner._detect_article_context(input_data)
    print("Article context:", article_context)

    # Check if article was found
    if article_context.get("article_id"):
        print(f"✓ Article found: ID {article_context['article_id']}")
        print(f"  URL: {article_context.get('url')}")
        print(f"  Title: {article_context.get('title')}")
    else:
        print("✗ No article found in database")


if __name__ == "__main__":
    asyncio.run(debug_article_detection())
