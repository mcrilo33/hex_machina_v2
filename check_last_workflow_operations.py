#!/usr/bin/env python3
"""
Script to check the last workflow operation IDs in the database.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import desc

from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import EnrichmentDB


def check_last_workflow_operations():
    """Check the last workflow operation IDs in the database."""
    try:
        # Get storage manager
        storage_manager = get_storage_manager()

        # Query enrichments table for recent workflow operations
        with storage_manager.session() as session:
            # Get all enrichments with workflow_operation_id, ordered by creation time
            enrichments = (
                session.query(EnrichmentDB)
                .filter(EnrichmentDB.workflow_operation_id.isnot(None))
                .order_by(desc(EnrichmentDB.created_at))
                .limit(20)  # Get last 20
                .all()
            )

            if not enrichments:
                print("📭 No enrichments with workflow_operation_id found in database")
                return

            print(
                f"📊 Found {len(enrichments)} enrichments with workflow_operation_id:"
            )
            print("=" * 80)

            # Group by workflow_operation_id
            workflow_groups = {}
            for enrichment in enrichments:
                workflow_id = enrichment.workflow_operation_id
                if workflow_id not in workflow_groups:
                    workflow_groups[workflow_id] = []
                workflow_groups[workflow_id].append(enrichment)

            # Display grouped results
            for i, (workflow_id, enrichments_list) in enumerate(
                workflow_groups.items(), 1
            ):
                print(f"\n{i}. Workflow Operation ID: {workflow_id}")
                print(f"   Articles processed: {len(enrichments_list)}")
                print(f"   First created: {enrichments_list[-1].created_at}")
                print(f"   Last created: {enrichments_list[0].created_at}")
                print(f"   Task: {enrichments_list[0].tool_name}")

                # Show article IDs
                article_ids = [e.article_id for e in enrichments_list]
                print(
                    f"   Article IDs: {article_ids[:5]}{'...' if len(article_ids) > 5 else ''}"
                )

                print("-" * 60)

            # Show most recent individual enrichments
            print("\n📋 Most Recent Individual Enrichments:")
            print("=" * 80)

            for i, enrichment in enumerate(enrichments[:10], 1):
                print(f"{i:2d}. ID: {enrichment.id}")
                print(f"    Workflow ID: {enrichment.workflow_operation_id}")
                print(f"    Article ID: {enrichment.article_id}")
                print(f"    Task: {enrichment.tool_name}")
                print(f"    Created: {enrichment.created_at}")
                print()

    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    check_last_workflow_operations()
