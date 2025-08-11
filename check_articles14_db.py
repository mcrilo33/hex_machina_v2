#!/usr/bin/env python3
"""
Script to directly check the articles14.db DuckDB database.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import duckdb


def check_articles14_db():
    """Check the articles14.db DuckDB database directly."""
    db_path = Path("storage/articles14.db")

    if not db_path.exists():
        print(f"❌ Database file not found: {db_path}")
        return

    print(f"🔍 Checking DuckDB database: {db_path}")
    print(f"📏 File size: {db_path.stat().st_size / (1024*1024):.1f} MB")
    print("=" * 60)

    try:
        # Connect to DuckDB database
        conn = duckdb.connect(str(db_path))

        # Get table list
        tables_result = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main';"
        )
        tables = [row[0] for row in tables_result.fetchall()]

        print(f"📋 Tables found: {len(tables)}")
        for table in tables:
            print(f"  - {table}")
        print()

        # Check articles table schema
        if "articles" in tables:
            print("📋 Articles table schema:")
            schema_result = conn.execute("DESCRIBE articles;")
            schema = schema_result.fetchall()
            for col in schema:
                print(f"  - {col[0]}: {col[1]}")
            print()

            article_count = conn.execute("SELECT COUNT(*) FROM articles;").fetchone()[0]
            print(f"📊 Total Articles: {article_count}")

            if article_count > 0:
                # Get recent articles using correct column names
                recent_articles = conn.execute(
                    """
                    SELECT id, title, url_domain, ingested_at 
                    FROM articles 
                    ORDER BY ingested_at DESC 
                    LIMIT 5;
                """
                ).fetchall()

                print("\n📋 Recent Articles:")
                for article in recent_articles:
                    title = (
                        article[1][:50] + "..." if len(article[1]) > 50 else article[1]
                    )
                    print(
                        f"  ID: {article[0]}, Title: {title}, Domain: {article[2]}, Ingested: {article[3]}"
                    )

        # Check enrichments table schema
        if "enrichments" in tables:
            print("\n📋 Enrichments table schema:")
            schema_result = conn.execute("DESCRIBE enrichments;")
            schema = schema_result.fetchall()
            for col in schema:
                print(f"  - {col[0]}: {col[1]}")
            print()

            enrichment_count = conn.execute(
                "SELECT COUNT(*) FROM enrichments;"
            ).fetchone()[0]
            print(f"📊 Total Enrichments: {enrichment_count}")

            if enrichment_count > 0:
                # Get enrichments with workflow_operation_id
                workflow_count = conn.execute(
                    """
                    SELECT COUNT(*) FROM enrichments 
                    WHERE workflow_operation_id IS NOT NULL;
                """
                ).fetchone()[0]
                print(f"📊 Enrichments with workflow_operation_id: {workflow_count}")

                # Get recent enrichments using correct column names
                recent_enrichments = conn.execute(
                    """
                    SELECT id, article_id, tool_name, workflow_operation_id, created_at 
                    FROM enrichments 
                    ORDER BY created_at DESC 
                    LIMIT 5;
                """
                ).fetchall()

                print("\n📋 Recent Enrichments:")
                for enrichment in recent_enrichments:
                    workflow_id = enrichment[3] or "None"
                    print(
                        f"  ID: {enrichment[0]}, Article: {enrichment[1]}, Task: {enrichment[2]}, Workflow: {workflow_id}, Created: {enrichment[4]}"
                    )

                # Get unique workflow operation IDs
                if workflow_count > 0:
                    workflow_groups = conn.execute(
                        """
                        SELECT workflow_operation_id, COUNT(*) as count
                        FROM enrichments 
                        WHERE workflow_operation_id IS NOT NULL
                        GROUP BY workflow_operation_id
                        ORDER BY count DESC;
                    """
                    ).fetchall()

                    print("\n🔗 Workflow Operation Groups:")
                    for workflow_id, count in workflow_groups:
                        print(f"  {workflow_id}: {count} enrichments")

                    # Show the most recent workflow operation IDs
                    print("\n🚀 Most Recent Workflow Operation IDs:")
                    recent_workflows = conn.execute(
                        """
                        SELECT DISTINCT workflow_operation_id, MAX(created_at) as last_created
                        FROM enrichments 
                        WHERE workflow_operation_id IS NOT NULL
                        GROUP BY workflow_operation_id
                        ORDER BY last_created DESC
                        LIMIT 10;
                    """
                    ).fetchall()

                    for i, (workflow_id, last_created) in enumerate(
                        recent_workflows, 1
                    ):
                        print(f"  {i:2d}. {workflow_id}")
                        print(f"      Last activity: {last_created}")
                        print()

        conn.close()

    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    check_articles14_db()
