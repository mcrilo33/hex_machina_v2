#!/usr/bin/env python3
"""Test script to query database and get an article."""

import json

from src.hex_machina.storage.manager import get_storage_manager


def get_sample_article():
    """Get a sample article from the database."""
    try:
        storage_manager = get_storage_manager("storage/articles14.db")

        # Get all articles
        articles = storage_manager.get_all_articles()

        if articles:
            print(f"Found {len(articles)} articles in database")

            # Get the first article
            article = articles[0]
            print(f"Sample article ID: {article.id}")
            print(f"Sample article title: {article.title}")
            print(f"Sample article URL: {article.url}")
            print(f"Sample article domain: {article.url_domain}")
            print(
                f"Sample article content length: {len(article.text_content) if article.text_content else 0}"
            )

            # Save to file for testing
            article_data = {
                "id": article.id,
                "title": article.title,
                "url": article.url,
                "domain": article.url_domain,
                "content": article.text_content,
            }

            with open("test_db_article_input.json", "w") as f:
                json.dump(article_data, f, indent=2)

            print("Saved article data to test_db_article_input.json")

            return article_data
        else:
            print("No articles found in database")
            return None

    except Exception as e:
        print(f"Error querying database: {e}")
        return None


if __name__ == "__main__":
    article = get_sample_article()
    if article:
        print("\n" + "=" * 50)
        print("SAMPLE ARTICLE FOR TESTING:")
        print("=" * 50)
        print(f"ID: {article['id']}")
        print(f"Title: {article['title']}")
        print(f"URL: {article['url']}")
        print(f"Domain: {article['domain']}")
        print(f"Content length: {len(article['content']) if article['content'] else 0}")
        print("=" * 50)
