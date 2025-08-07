"""Example usage of the ContentCompletenessEvaluator with OpenRouter."""

import asyncio
import logging

from src.hex_machina.enrichment.evaluation.langchain.chains.evaluation_chains import (
    ContentCompletenessEvaluator,
)
from src.hex_machina.enrichment.llm.config import LLMConfig, create_evaluation_llm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockArticle:
    """Mock article class for testing."""

    def __init__(self, title: str, content: str, url: str):
        self.title = title
        self.text_content = content
        self.url = url


async def evaluate_single_article():
    """Example: Evaluate a single article for completeness."""

    # Initialize the LLM with OpenRouter
    llm = create_evaluation_llm("gpt-3.5-turbo")

    # Create the evaluator
    evaluator = ContentCompletenessEvaluator(llm=llm, logger=logger)

    # Create a mock article
    article = MockArticle(
        title="Sample Article",
        content="This is a complete article with substantial content. It contains multiple paragraphs and provides comprehensive information on the topic. The article flows naturally and concludes properly.",
        url="https://example.com/article1",
    )

    # Evaluate the article
    result = await evaluator.evaluate_article(article)

    # Print results
    print(f"Article: {result.url}")
    print(f"Is Complete: {result.is_complete}")
    print(f"Detected Issues: {result.detected_issues}")
    print(f"Processing Time: {result.processing_time_seconds:.2f}s")


async def evaluate_multiple_articles():
    """Example: Evaluate multiple articles concurrently for completeness."""

    # Initialize the LLM with OpenRouter
    llm = create_evaluation_llm("gpt-3.5-turbo")

    # Create the evaluator
    evaluator = ContentCompletenessEvaluator(llm=llm, logger=logger)

    # Create mock articles
    articles = [
        MockArticle(
            title="Complete Article",
            content="This is a complete article with substantial content. It contains multiple paragraphs and provides comprehensive information on the topic. The article flows naturally and concludes properly.",
            url="https://example.com/complete",
        ),
        MockArticle(
            title="Paywall Article",
            content="This article is behind a paywall. Please subscribe to continue reading. Premium content requires a subscription.",
            url="https://example.com/paywall",
        ),
        MockArticle(
            title="Truncated Article",
            content="This article appears to be truncated. The content ends abruptly without proper conclusion. Read more to see the full article.",
            url="https://example.com/truncated",
        ),
        MockArticle(
            title="Anti-bot Page",
            content="Please enable JavaScript to view this content. Access denied. Please complete the CAPTCHA to continue.",
            url="https://example.com/antibot",
        ),
    ]

    # Evaluate all articles concurrently
    results = await evaluator.evaluate_articles(articles)

    # Print results
    for result in results:
        print(f"\nArticle: {result.url}")
        print(f"  Is Complete: {result.is_complete}")
        print(f"  Detected Issues: {result.detected_issues}")


async def compare_models():
    """Example: Compare different models available through OpenRouter."""

    # Test different models
    models = [
        "gpt-3.5-turbo",
        "claude-3-haiku",
        "gemini-pro",
    ]

    article = MockArticle(
        title="Test Article",
        content="This is a complete article with substantial content. It contains multiple paragraphs and provides comprehensive information on the topic.",
        url="https://example.com/test",
    )

    for model in models:
        print(f"\n=== Testing Model: {model} ===")
        try:
            llm = create_evaluation_llm(model)
            evaluator = ContentCompletenessEvaluator(llm=llm, logger=logger)

            start_time = asyncio.get_event_loop().time()
            result = await evaluator.evaluate_article(article)
            end_time = asyncio.get_event_loop().time()

            print(f"Result: {result.is_complete}")
            print(f"Issues: {result.detected_issues}")
            print(f"Time: {end_time - start_time:.2f}s")

        except Exception as e:
            print(f"Error with {model}: {e}")


async def main():
    """Main function to run examples."""
    # Check if API key is configured
    if not LLMConfig.validate_api_key():
        print("❌ OpenRouter API key not found!")
        print("Please set the OPENROUTER_API_KEY environment variable.")
        print("You can get your API key from: https://openrouter.ai/keys")
        return

    print("✅ OpenRouter API key configured")
    print(f"Available models: {list(LLMConfig.list_available_models().keys())}")

    print("\n=== Single Article Completeness Evaluation ===")
    await evaluate_single_article()

    print("\n=== Multiple Articles Completeness Evaluation ===")
    await evaluate_multiple_articles()

    print("\n=== Model Comparison ===")
    await compare_models()


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
