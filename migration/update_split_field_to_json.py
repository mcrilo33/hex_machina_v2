#!/usr/bin/env python3
"""
Migration script to update the split field in dataset_examples table from String to JSON.

This allows the split field to store either a single split name (string) or multiple split names (list).
"""

import json
import sqlite3
from pathlib import Path


def migrate_split_field():
    """Migrate the split field from String to JSON in dataset_examples table."""

    print("🔄 Starting split field migration...")

    try:
        # Find the database file
        db_path = Path("storage/articles14.db")
        if not db_path.exists():
            print(f"❌ Database not found at {db_path}")
            return False

        print(f"📁 Using database: {db_path}")

        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check current table structure
        cursor.execute("PRAGMA table_info(dataset_examples)")
        result = cursor.fetchall()

        print("📊 Current table structure:")
        for row in result:
            print(f"   {row[1]} ({row[2]}) - {'NOT NULL' if row[3] else 'NULL'}")

        # Check if split field exists
        split_column_info = next((row for row in result if row[1] == "split"), None)

        if not split_column_info:
            print("❌ Split field not found in table")
            return False

        print(f"🔄 Split field is currently {split_column_info[2]}")

        # Create a backup of the current split data
        print("💾 Backing up current split data...")
        cursor.execute("SELECT id, split FROM dataset_examples WHERE split IS NOT NULL")
        backup_result = cursor.fetchall()

        split_backup = {row[0]: row[1] for row in backup_result}
        print(f"   Backed up {len(split_backup)} examples with split data")

        # Update the split field to JSON type
        print("🔄 Updating split field to JSON type...")

        # SQLite doesn't support ALTER COLUMN TYPE directly, so we need to:
        # 1. Create a new table with the desired schema
        # 2. Copy data, converting split values to JSON format
        # 3. Drop old table and rename new one

        # Create new table
        cursor.execute(
            """
            CREATE TABLE dataset_examples_new (
                id INTEGER PRIMARY KEY,
                dataset_id INTEGER NOT NULL,
                article_id INTEGER NOT NULL,
                inputs TEXT NOT NULL,
                outputs TEXT,
                example_metadata TEXT,
                split TEXT,
                langsmith_example_id TEXT,
                created_at TEXT,
                FOREIGN KEY (dataset_id) REFERENCES datasets (id),
                FOREIGN KEY (article_id) REFERENCES articles (id)
            )
        """
        )

        # Copy data, converting split to JSON format
        print("📋 Copying data with split conversion...")
        cursor.execute(
            """
            INSERT INTO dataset_examples_new 
            SELECT 
                id, dataset_id, article_id, inputs, outputs, 
                example_metadata, split, langsmith_example_id, created_at
            FROM dataset_examples
        """
        )

        # Drop old table and rename new one
        cursor.execute("DROP TABLE dataset_examples")
        cursor.execute("ALTER TABLE dataset_examples_new RENAME TO dataset_examples")

        # Recreate indexes and constraints
        cursor.execute(
            """
            CREATE INDEX ix_dataset_examples_dataset_id ON dataset_examples (dataset_id)
        """
        )
        cursor.execute(
            """
            CREATE INDEX ix_dataset_examples_article_id ON dataset_examples (article_id)
        """
        )
        cursor.execute(
            """
            CREATE INDEX ix_dataset_examples_split ON dataset_examples (split)
        """
        )

        # Convert existing split values to JSON format
        print("🔄 Converting existing split values to JSON format...")
        for example_id, old_split in split_backup.items():
            if old_split:
                # Convert to JSON format (single string becomes list with one item)
                new_split = json.dumps([old_split])
                cursor.execute(
                    "UPDATE dataset_examples SET split = ? WHERE id = ?",
                    (new_split, example_id),
                )
                print(f"   Example {example_id}: '{old_split}' -> {new_split}")

        conn.commit()

        # Verify the migration
        print("🔍 Verifying migration...")
        cursor.execute("PRAGMA table_info(dataset_examples)")
        result = cursor.fetchall()

        split_column_info = next((row for row in result if row[1] == "split"), None)

        if (
            split_column_info and split_column_info[2] == "TEXT"
        ):  # SQLite stores JSON as TEXT
            print("✅ Migration successful! Split field is now JSON type")

            # Show some examples
            cursor.execute(
                "SELECT id, split FROM dataset_examples WHERE split IS NOT NULL LIMIT 5"
            )
            examples_result = cursor.fetchall()

            print("📋 Sample split data after migration:")
            for row in examples_result:
                print(f"   Example {row[0]}: {row[1]}")

        else:
            print("❌ Migration failed - split field type not updated")
            return False

        conn.close()

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("🎉 Split field migration completed successfully!")
    return True


if __name__ == "__main__":
    print("🚀 Dataset Examples Split Field Migration")
    print("=" * 50)
    print()

    success = migrate_split_field()

    if success:
        print("\n✅ Migration completed successfully!")
        print("   The split field now supports both single splits and multiple splits")
        print("   - Single split: 'train'")
        print("   - Multiple splits: ['train', 'small']")
        print("   - No split: NULL (default split)")
    else:
        print("\n❌ Migration failed!")
        exit(1)
