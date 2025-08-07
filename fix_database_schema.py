#!/usr/bin/env python3
"""Fix database schema to make workflow_operation_id nullable."""

import asyncio

from sqlalchemy import text

from src.hex_machina.enrichment.config.database_config import DatabaseConfigManager
from src.hex_machina.storage.manager import get_storage_manager


async def fix_database_schema():
    """Fix the database schema to make workflow_operation_id nullable."""

    try:
        # Get database path from config
        database_config_manager = DatabaseConfigManager()
        db_path = database_config_manager.get_db_path()
        print(f"Fixing database schema for: {db_path}")

        # Get storage manager
        storage_manager = get_storage_manager(db_path)

        # Alter the table to make workflow_operation_id nullable
        with storage_manager.session() as session:
            # Execute ALTER TABLE command
            session.execute(
                text(
                    "ALTER TABLE enrichments ALTER COLUMN workflow_operation_id DROP NOT NULL"
                )
            )
            session.commit()
            print("✓ Successfully made workflow_operation_id nullable")

    except Exception as e:
        print(f"Error fixing database schema: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(fix_database_schema())
