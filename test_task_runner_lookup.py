#!/usr/bin/env python3
"""Test that mimics exactly what the task runner does for article lookup."""

import asyncio
import json

from src.hex_machina.enrichment.config.database_config import database_config_manager
from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import ArticleDB


async def test_task_runner_lookup():
    """Test that mimics exactly what the task runner does."""

    print("=== Testing Task Runner Lookup Logic ===\n")

    # Load test data (same as task runner)
    with open("test_db_article_input.json", "r") as f:
        input_data = json.load(f)

    print("Input data keys:", list(input_data.keys()))
    print("Input data ID:", input_data.get("id"))

    # Mimic the exact lookup logic from task runner
    print("\n--- Mimicking Task Runner Lookup ---")

    # Check for direct article ID (same as task runner)
    if "id" in input_data:
        print(f"Checking article ID: {input_data['id']}")

        try:
            db_path = database_config_manager.get_db_path()
            print(f"Database path: {db_path}")

            storage_manager = get_storage_manager(db_path)
            with storage_manager.session() as session:
                article = (
                    session.query(ArticleDB)
                    .filter(ArticleDB.id == input_data["id"])
                    .first()
                )
                if article:
                    print(f"✓ Found article by ID {input_data['id']}: {article.title}")
                    print(f"  URL: {article.url}")
                    print(f"  Domain: {article.url_domain}")
                else:
                    print(f"✗ No article found by ID {input_data['id']}")
        except Exception as e:
            print(f"Error in lookup: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_task_runner_lookup())
