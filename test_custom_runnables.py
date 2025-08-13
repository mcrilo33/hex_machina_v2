"""Test script for custom LangChain runnables."""

import asyncio
import logging

from src.hex_machina.langchain_tasks.runnables import runnable_registry

# Set up logging
logging.basicConfig(level=logging.INFO)


async def test_article_fetcher():
    """Test the ArticleFetcher runnable."""
    print("Testing ArticleFetcher...")

    # Get the runnable class from registry
    ArticleFetcherClass = runnable_registry.get("ArticleFetcher")

    # Create instance
    fetcher = ArticleFetcherClass(
        db_path="storage/articles14.db",
        filters={"domain": "techcrunch.com", "date_range": "last_7_days", "limit": 5},
    )

    # Test invoke
    try:
        articles = fetcher.invoke({})
        print(f"✅ ArticleFetcher successful: {len(articles)} articles")
        if articles:
            print(f"First article: {articles[0]}")
    except Exception as e:
        print(f"❌ ArticleFetcher failed: {e}")

    # Cleanup
    fetcher.__del__()


async def test_enrichment_saver():
    """Test the EnrichmentSaver runnable."""
    print("\nTesting EnrichmentSaver...")

    # Get the runnable class from registry
    EnrichmentSaverClass = runnable_registry.get("EnrichmentSaver")

    # Create instance
    saver = EnrichmentSaverClass(
        db_path="storage/articles14.db",
        enrichment_type="test_keywords",
        input_mapping="extract_keywords.keywords",
    )

    # Test invoke with mock data
    mock_inputs = {
        "article_id": 1,
        "extract_keywords": {"keywords": ["AI", "machine learning", "technology"]},
    }

    try:
        result = saver.invoke(mock_inputs)
        print(f"✅ EnrichmentSaver successful: {result}")
    except Exception as e:
        print(f"❌ EnrichmentSaver failed: {e}")

    # Cleanup
    saver.__del__()


async def test_registry():
    """Test the runnable registry."""
    print("\nTesting RunnableRegistry...")

    # List available runnables
    available = runnable_registry.list_available()
    print(f"Available runnables: {available}")

    # Test getting runnables
    try:
        ArticleFetcherClass = runnable_registry.get("ArticleFetcher")
        EnrichmentSaverClass = runnable_registry.get("EnrichmentSaver")
        print("✅ Registry successful: both runnables found")
    except Exception as e:
        print(f"❌ Registry failed: {e}")


async def main():
    """Run all tests."""
    print("🧪 Testing Custom LangChain Runnables\n")

    await test_registry()
    await test_article_fetcher()
    await test_enrichment_saver()

    print("\n✨ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
