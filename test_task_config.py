"""Test script for the custom runnables task configuration."""

import asyncio
import logging

from src.hex_machina.langchain_tasks.runnables import runnable_registry

# Set up logging
logging.basicConfig(level=logging.INFO)


async def test_task_execution():
    """Test the complete task execution flow."""
    print("🧪 Testing Custom Runnables Task Configuration\n")

    # Check available runnables
    available = runnable_registry.list_available()
    print(f"Available runnables: {available}")

    # Test each runnable individually
    await test_article_fetcher()
    await test_mock_summarizer()
    await test_mock_keyword_extractor()
    await test_enrichment_saver()

    print("\n✨ All individual runnable tests completed!")
    print("\n📋 Task Configuration Summary:")
    print("✅ ArticleFetcher - fetches articles from database")
    print("✅ MockSummarizer - generates mock summaries")
    print("✅ MockKeywordExtractor - extracts mock keywords")
    print("✅ EnrichmentSaver - saves enrichments to database")
    print("✅ Dataset generation enabled at both step and task levels")


async def test_article_fetcher():
    """Test ArticleFetcher with real database."""
    print("\n📚 Testing ArticleFetcher...")

    ArticleFetcherClass = runnable_registry.get("ArticleFetcher")
    fetcher = ArticleFetcherClass(db_path="storage/articles14.db", filters={"limit": 2})

    try:
        articles = fetcher.invoke({})
        print(f"✅ Fetched {len(articles)} articles")
        if articles:
            print(f"   First article: {articles[0].get('title', 'No title')[:50]}...")
    except Exception as e:
        print(f"❌ ArticleFetcher failed: {e}")
    finally:
        fetcher.__del__()


async def test_mock_summarizer():
    """Test MockSummarizer."""
    print("\n📝 Testing MockSummarizer...")

    MockSummarizerClass = runnable_registry.get("MockSummarizer")
    summarizer = MockSummarizerClass(summary_length="short")

    # Mock input with articles
    mock_inputs = {
        "fetch_sample_articles": [
            {"id": 1, "title": "AI Breakthrough in Machine Learning"},
            {"id": 2, "title": "New Business Strategy for Startups"},
        ]
    }

    try:
        result = summarizer.invoke(mock_inputs)
        summaries = result.get("generate_article_summary", {}).get("summaries", [])
        print(f"✅ Generated {len(summaries)} summaries")
        for summary in summaries:
            print(f"   Article {summary['article_id']}: {summary['summary'][:60]}...")
    except Exception as e:
        print(f"❌ MockSummarizer failed: {e}")


async def test_mock_keyword_extractor():
    """Test MockKeywordExtractor."""
    print("\n🔑 Testing MockKeywordExtractor...")

    MockKeywordExtractorClass = runnable_registry.get("MockKeywordExtractor")
    extractor = MockKeywordExtractorClass(max_keywords=3)

    # Mock input with articles
    mock_inputs = {
        "fetch_sample_articles": [
            {
                "id": 1,
                "title": "AI Breakthrough",
                "text_content": "machine learning technology",
            },
            {
                "id": 2,
                "title": "Business Strategy",
                "text_content": "startup finance market",
            },
        ]
    }

    try:
        result = extractor.invoke(mock_inputs)
        keywords_list = result.get("extract_keywords", {}).get("keywords", [])
        print(f"✅ Extracted keywords for {len(keywords_list)} articles")
        for item in keywords_list:
            print(f"   Article {item['article_id']}: {', '.join(item['keywords'])}")
    except Exception as e:
        print(f"❌ MockKeywordExtractor failed: {e}")


async def test_enrichment_saver():
    """Test EnrichmentSaver."""
    print("\n💾 Testing EnrichmentSaver...")

    EnrichmentSaverClass = runnable_registry.get("EnrichmentSaver")
    saver = EnrichmentSaverClass(
        db_path="storage/articles14.db",
        enrichment_type="test_keywords",
        input_mapping="extract_keywords.keywords",
    )

    # Mock input with keywords
    mock_inputs = {
        "article_id": 999,  # Test article ID
        "extract_keywords": {"keywords": ["AI", "machine learning", "technology"]},
    }

    try:
        result = saver.invoke(mock_inputs)
        print("✅ Enrichment saved successfully")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"❌ EnrichmentSaver failed: {e}")
    finally:
        saver.__del__()


if __name__ == "__main__":
    asyncio.run(test_task_execution())
