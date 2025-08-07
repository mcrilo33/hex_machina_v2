#!/usr/bin/env python3
"""Test the lookup methods directly."""

import asyncio

from src.hex_machina.enrichment.tasks.runner import task_runner


async def test_lookup_methods():
    """Test the lookup methods directly."""

    print("Testing _find_article_by_id method...")
    article = task_runner._find_article_by_id(1)
    if article:
        print(f"✓ Found article by ID: {article.id}")
        print(f"  Title: {article.title}")
        print(f"  URL: {article.url}")
        print(f"  Domain: {article.url_domain}")
    else:
        print("✗ Article not found by ID")

    print("\nTesting _find_article_by_url method...")
    article = task_runner._find_article_by_url(
        "https://www.philschmid.de/memory-in-agents"
    )
    if article:
        print(f"✓ Found article by URL: {article.id}")
        print(f"  Title: {article.title}")
        print(f"  URL: {article.url}")
        print(f"  Domain: {article.url_domain}")
    else:
        print("✗ Article not found by URL")

    print("\nTesting _find_article_by_title_domain method...")
    article = task_runner._find_article_by_title_domain(
        "Memory in Agents, Make LLMs remember.", "www.philschmid.de"
    )
    if article:
        print(f"✓ Found article by title/domain: {article.id}")
        print(f"  Title: {article.title}")
        print(f"  URL: {article.url}")
        print(f"  Domain: {article.url_domain}")
    else:
        print("✗ Article not found by title/domain")


if __name__ == "__main__":
    asyncio.run(test_lookup_methods())
