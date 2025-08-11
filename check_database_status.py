#!/usr/bin/env python3
"""
Script to check the overall database status and enrichments table.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import desc

from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import ArticleDB, EnrichmentDB


def check_database_status():
    """Check the overall database status."""
    try:
        # Get storage manager
        storage_manager = get_storage_manager()

        print("🔍 Database Status Check")
        print("=" * 60)

        with storage_manager.session() as session:
            # Check total counts
            total_articles = session.query(ArticleDB).count()
            total_enrichments = session.query(EnrichmentDB).count()

            print(f"📊 Total Articles: {total_articles}")
            print(f"📊 Total Enrichments: {total_enrichments}")
            print()

            if total_enrichments == 0:
                print("📭 No enrichments found in database")
                return

            # Check enrichments with workflow_operation_id
            enrichments_with_workflow = (
                session.query(EnrichmentDB)
                .filter(EnrichmentDB.workflow_operation_id.isnot(None))
                .count()
            )

            enrichments_without_workflow = (
                session.query(EnrichmentDB)
                .filter(EnrichmentDB.workflow_operation_id.isnull())
                .count()
            )

            print(
                f"🔗 Enrichments with workflow_operation_id: {enrichments_with_workflow}"
            )
            print(
                f"🔗 Enrichments without workflow_operation_id: {enrichments_without_workflow}"
            )
            print()

            # Show recent enrichments
            print("📋 Recent Enrichments (Last 10):")
            print("-" * 60)

            recent_enrichments = (
                session.query(EnrichmentDB)
                .order_by(desc(EnrichmentDB.created_at))
                .limit(10)
                .all()
            )

            for i, enrichment in enumerate(recent_enrichments, 1):
                print(f"{i:2d}. ID: {enrichment.id}")
                print(f"    Article ID: {enrichment.article_id}")
                print(f"    Task: {enrichment.tool_name}")
                print(f"    Workflow ID: {enrichment.workflow_operation_id or 'None'}")
                print(f"    Created: {enrichment.created_at}")
                print()

            # Check workflow_operation_id column type
            print("🔍 Database Schema Check:")
            print("-" * 60)

            # Get column info
            from sqlalchemy import inspect

            inspector = inspect(storage_manager.engine)

            try:
                columns = inspector.get_columns("enrichments")
                for column in columns:
                    if column["name"] == "workflow_operation_id":
                        print("📋 workflow_operation_id column:")
                        print(f"    Type: {column['type']}")
                        print(f"    Nullable: {column['nullable']}")
                        print(f"    Default: {column.get('default', 'None')}")
                        break
            except Exception as e:
                print(f"⚠️ Could not inspect schema: {e}")

    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    check_database_status()
