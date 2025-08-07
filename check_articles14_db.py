#!/usr/bin/env python3
"""Check what articles are in the articles14.db database."""

import asyncio

from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import ArticleDB


async def check_articles14_db():
    """Check articles in the articles14.db database."""
    try:
        storage_manager = get_storage_manager("storage/articles14.db")

        with storage_manager.session() as session:
            articles = session.query(ArticleDB).limit(10).all()

            print(f"Found {len(articles)} articles in articles14.db (showing first 10)")

            if articles:
                print("\nFirst 10 articles:")
                for article in articles:
                    print(f"  ID: {article.id}")
                    print(f"  Title: {article.title[:50]}...")
                    print(f"  URL: {article.url}")
                    print(f"  Domain: {article.url_domain}")
                    print("  ---")
            else:
                print("No articles found in articles14.db")

    except Exception as e:
        print(f"Error checking articles14.db: {e}")


if __name__ == "__main__":
    asyncio.run(check_articles14_db())
