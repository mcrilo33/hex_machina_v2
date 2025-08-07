#!/usr/bin/env python3
"""Check if enrichment was saved to the database."""

from src.hex_machina.storage.manager import get_storage_manager


def check_enrichments():
    """Check enrichments in the database."""
    try:
        storage_manager = get_storage_manager("storage/articles14.db")

        # Get the session
        with storage_manager.session() as session:
            # Check if enrichments table exists and has data
            from src.hex_machina.storage.models import EnrichmentDB

            enrichments = session.query(EnrichmentDB).all()
            print(f"Found {len(enrichments)} enrichments in database")

            if enrichments:
                print("\nRecent enrichments:")
                for enrichment in enrichments[-5:]:  # Show last 5
                    print(f"  ID: {enrichment.id}")
                    print(f"  Article ID: {enrichment.article_id}")
                    print(f"  Type: {enrichment.enrichment_type}")
                    print(f"  Source: {enrichment.source}")
                    print(f"  Tool: {enrichment.tool_name}")
                    print(f"  Created: {enrichment.created_at}")
                    print(f"  Data: {enrichment.enrichment_data}")
                    print("  ---")
            else:
                print("No enrichments found in database")

    except Exception as e:
        print(f"Error checking enrichments: {e}")


if __name__ == "__main__":
    check_enrichments()
