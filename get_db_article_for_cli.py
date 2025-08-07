#!/usr/bin/env python3
"""Get an article from the database and format it for CLI input."""

import asyncio
import json

from src.hex_machina.enrichment.config.database_config import DatabaseConfigManager
from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import ArticleDB


async def get_db_article_for_cli(article_id: int = 1):
    """Get an article from the database and format it for CLI input."""

    try:
        # Get database path from config
        database_config_manager = DatabaseConfigManager()
        db_path = database_config_manager.get_db_path()

        # Get storage manager
        storage_manager = get_storage_manager(db_path)

        with storage_manager.session() as session:
            article = (
                session.query(ArticleDB).filter(ArticleDB.id == article_id).first()
            )

            if article:
                # Format article for CLI input
                article_data = {
                    "id": article.id,
                    "title": article.title,
                    "url": article.url,
                    "domain": article.url_domain,
                    "content": article.text_content,
                }

                # Save to file for CLI use
                output_file = f"db_article_{article_id}_input.json"
                with open(output_file, "w") as f:
                    json.dump(article_data, f, indent=2)

                print(f"✓ Retrieved article ID {article_id}: {article.title}")
                print(f"✓ Saved to: {output_file}")
                print(f"✓ Content length: {len(article.text_content)} characters")

                return output_file
            else:
                print(f"✗ Article ID {article_id} not found in database")
                return None

    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    import sys

    article_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(get_db_article_for_cli(article_id))
