#!/usr/bin/env python3
"""Check if enrichments were saved to the database."""

import asyncio

from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import EnrichmentDB


async def check_enrichments():
    """Check enrichments in the database."""
    try:
        # Get storage manager using configured path
        from src.hex_machina.enrichment.config.database_config import (
            DatabaseConfigManager,
        )

        database_config_manager = DatabaseConfigManager()
        db_path = database_config_manager.get_db_path()
        print(f"Using database path: {db_path}")

        storage_manager = get_storage_manager(db_path)

        # Query enrichments
        with storage_manager.session() as session:
            enrichments = session.query(EnrichmentDB).all()

            print(f"Found {len(enrichments)} enrichments in database")

            if enrichments:
                print("\nRecent enrichments:")
                for enrichment in enrichments[-5:]:  # Show last 5
                    print(f"  ID: {enrichment.id}")
                    print(f"  Tool: {enrichment.tool_name}")
                    print(f"  Article ID: {enrichment.article_id}")
                    print(f"  Created: {enrichment.created_at}")
                    print(f"  Output: {enrichment.enrichment_data}")
                    print("  ---")
            else:
                print("No enrichments found in database")

    except Exception as e:
        print(f"Error checking enrichments: {e}")


if __name__ == "__main__":
    asyncio.run(check_enrichments())
