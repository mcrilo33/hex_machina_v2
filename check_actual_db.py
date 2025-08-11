#!/usr/bin/env python3
"""Check what's actually in the articles14.db database."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import text

from src.hex_machina.storage.manager import get_storage_manager


def check_actual_db():
    """Check what's actually in the articles14.db database."""
    print("🔍 Checking articles14.db Database")
    print("=" * 50)

    # Use the correct database path from config
    db_path = "storage/articles14.db"
    print(f"Database path: {db_path}")

    storage = get_storage_manager(db_path)

    with storage.session() as session:
        # Check if the database file exists and has tables
        try:
            # Check datasets table
            result = session.execute(text("SELECT COUNT(*) FROM datasets"))
            dataset_count = result.fetchone()[0]
            print(f"📁 Datasets in database: {dataset_count}")

            if dataset_count > 0:
                result = session.execute(
                    text(
                        "SELECT id, name, description, langsmith_dataset_id FROM datasets ORDER BY id"
                    )
                )
                datasets = result.fetchall()
                for dataset in datasets:
                    print(
                        f"   ID: {dataset[0]}, Name: {dataset[1]}, LangSmith: {dataset[3]}"
                    )

            # Check dataset_examples table
            result = session.execute(text("SELECT COUNT(*) FROM dataset_examples"))
            example_count = result.fetchone()[0]
            print(f"📊 Examples in database: {example_count}")

            if example_count > 0:
                result = session.execute(
                    text(
                        "SELECT dataset_id, COUNT(*) as count FROM dataset_examples GROUP BY dataset_id"
                    )
                )
                examples = result.fetchall()
                for example in examples:
                    print(f"   Dataset ID {example[0]}: {example[1]} examples")

            # Check other tables
            result = session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                )
            )
            tables = result.fetchall()
            print("\n📋 Tables in database:")
            for table in tables:
                print(f"   {table[0]}")

        except Exception as e:
            print(f"❌ Error accessing database: {e}")


if __name__ == "__main__":
    check_actual_db()
