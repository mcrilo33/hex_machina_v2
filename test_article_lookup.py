#!/usr/bin/env python3
"""Test article lookup in database."""

from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import ArticleDB


def test_article_lookup():
    """Test looking up articles in the database."""
    try:
        storage_manager = get_storage_manager("storage/articles14.db")

        with storage_manager.session() as session:
            # Test 1: Get article by ID
            article = session.query(ArticleDB).filter(ArticleDB.id == 1).first()
            if article:
                print(f"Found article by ID 1: {article.title}")
                print(f"URL: {article.url}")
                print(f"URL Domain: {article.url_domain}")
                print(f"Source URL: {article.source_url}")

                # Test 2: Look up by URL
                article_by_url = (
                    session.query(ArticleDB)
                    .filter(ArticleDB.url == article.url)
                    .first()
                )
                if article_by_url:
                    print(f"✓ Found article by URL: {article_by_url.id}")
                else:
                    print("✗ Article not found by URL")

                # Test 3: Look up by title and domain
                article_by_title_domain = (
                    session.query(ArticleDB)
                    .filter(
                        ArticleDB.title == article.title,
                        ArticleDB.url_domain == article.url_domain,
                    )
                    .first()
                )
                if article_by_title_domain:
                    print(
                        f"✓ Found article by title/domain: {article_by_title_domain.id}"
                    )
                else:
                    print("✗ Article not found by title/domain")

                # Test 4: Check what happens with "domain" field
                print("\nTesting with 'domain' field:")
                print("Input has: domain = 'www.philschmid.de'")
                print(f"Database has: url_domain = '{article.url_domain}'")
                print(f"Match: {article.url_domain == 'www.philschmid.de'}")

            else:
                print("No article with ID 1 found")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_article_lookup()
