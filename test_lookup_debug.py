#!/usr/bin/env python3
"""Debug database connection and lookup with error handling."""

import asyncio

from src.hex_machina.enrichment.config.database_config import DatabaseConfigManager
from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import ArticleDB


async def test_database_connection():
    """Test database connection and lookup with detailed error handling."""

    try:
        # Get database path from config
        database_config_manager = DatabaseConfigManager()
        db_path = database_config_manager.get_db_path()
        print(f"Database path from config: {db_path}")

        # Test direct connection
        print("\nTesting direct database connection...")
        storage_manager = get_storage_manager(db_path)

        with storage_manager.session() as session:
            print("✓ Database connection successful")

            # Test query
            print("\nTesting article query...")
            articles = session.query(ArticleDB).limit(5).all()
            print(f"✓ Found {len(articles)} articles")

            if articles:
                print("\nFirst article details:")
                article = articles[0]
                print(f"  ID: {article.id}")
                print(f"  Title: {article.title}")
                print(f"  URL: {article.url}")
                print(f"  Domain: {article.url_domain}")

                # Test specific ID lookup
                print(f"\nTesting lookup for ID {article.id}...")
                found_article = (
                    session.query(ArticleDB).filter(ArticleDB.id == article.id).first()
                )
                if found_article:
                    print(f"✓ Found article by ID {article.id}")
                else:
                    print(f"✗ Article not found by ID {article.id}")

                # Test URL lookup
                print(f"\nTesting lookup for URL: {article.url}")
                found_article = (
                    session.query(ArticleDB)
                    .filter(ArticleDB.url == article.url)
                    .first()
                )
                if found_article:
                    print("✓ Found article by URL")
                else:
                    print("✗ Article not found by URL")

                # Test title/domain lookup
                print(
                    f"\nTesting lookup for title/domain: {article.title[:30]}... / {article.url_domain}"
                )
                found_article = (
                    session.query(ArticleDB)
                    .filter(
                        ArticleDB.title == article.title,
                        ArticleDB.url_domain == article.url_domain,
                    )
                    .first()
                )
                if found_article:
                    print("✓ Found article by title/domain")
                else:
                    print("✗ Article not found by title/domain")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_database_connection())
