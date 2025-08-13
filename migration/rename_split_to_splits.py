#!/usr/bin/env python3
"""
Migration script to rename the split field to splits in dataset_examples table.

This allows the splits field to store either a single split name (string) or multiple split names (list).
"""

from pathlib import Path

import duckdb


def migrate_split_to_splits():
    """Migrate the split field to splits in dataset_examples table."""

    print("🔄 Starting split to splits field migration...")

    try:
        # Find the database file
        db_path = Path("storage/articles14.db")
        if not db_path.exists():
            print(f"❌ Database not found at {db_path}")
            return False

        print(f"📁 Using database: {db_path}")

        # Connect to DuckDB database
        conn = duckdb.connect(str(db_path))

        # Check current table structure
        result = conn.execute("DESCRIBE dataset_examples").fetchall()

        print("📊 Current table structure:")
        for row in result:
            print(f"   {row[0]} ({row[1]}) - {'NOT NULL' if row[2] else 'NULL'}")

        # Check if split field exists
        split_column_info = next((row for row in result if row[0] == "split"), None)

        if not split_column_info:
            print("❌ Split field not found in table")
            return False

        print(f"🔄 Split field is currently {split_column_info[1]}")

        # Check if splits field already exists
        splits_column_info = next((row for row in result if row[0] == "splits"), None)

        if splits_column_info:
            print("✅ Splits field already exists - no migration needed")
            return True

        # Create a backup of the current split data
        print("💾 Backing up current split data...")
        backup_result = conn.execute(
            "SELECT id, split FROM dataset_examples WHERE split IS NOT NULL"
        ).fetchall()

        split_backup = {row[0]: row[1] for row in backup_result}
        print(f"   Backed up {len(split_backup)} examples with split data")

        # Add the new splits column
        print("🔄 Adding new splits column...")
        conn.execute("ALTER TABLE dataset_examples ADD COLUMN splits VARCHAR")

        # Copy data from split to splits, converting to JSON format
        print("📋 Copying data from split to splits with JSON conversion...")
        for example_id, old_split in split_backup.items():
            if old_split:
                # Convert to JSON format (single string becomes list with one item)
                new_splits = f'["{old_split}"]'
                conn.execute(
                    "UPDATE dataset_examples SET splits = ? WHERE id = ?",
                    [new_splits, example_id],
                )
                print(f"   Example {example_id}: '{old_split}' -> {new_splits}")

        # Drop the old split column
        print("🗑️ Dropping old split column...")
        conn.execute("ALTER TABLE dataset_examples DROP COLUMN split")

        # Verify the migration
        print("🔍 Verifying migration...")
        result = conn.execute("DESCRIBE dataset_examples").fetchall()

        splits_column_info = next((row for row in result if row[0] == "splits"), None)

        if splits_column_info:
            print("✅ Migration successful! Splits field is now available")

            # Show some examples
            examples_result = conn.execute(
                "SELECT id, splits FROM dataset_examples WHERE splits IS NOT NULL LIMIT 5"
            ).fetchall()

            print("📋 Sample splits data after migration:")
            for row in examples_result:
                print(f"   Example {row[0]}: {row[1]}")

        else:
            print("❌ Migration failed - splits field not found")
            return False

        conn.close()

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("🎉 Split to splits field migration completed successfully!")
    return True


if __name__ == "__main__":
    print("🚀 Dataset Examples Split to Splits Field Migration")
    print("=" * 55)
    print()

    success = migrate_split_to_splits()

    if success:
        print("\n✅ Migration completed successfully!")
        print("   The splits field now supports both single splits and multiple splits")
        print("   - Single split: 'train'")
        print("   - Multiple splits: ['train', 'small']")
        print("   - No splits: NULL (default split)")
    else:
        print("\n❌ Migration failed!")
        exit(1)
