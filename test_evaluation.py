#!/usr/bin/env python3
"""Simple test script for the ContentCompleteness evaluation system."""

import asyncio
import logging
import os
import sys

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from langchain_openai import ChatOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockArticle:
    """Mock article class for testing."""

    def __init__(self, title: str, content: str, url: str):
        self.title = title
        self.text_content = content
        self.url = url


def create_openrouter_llm(model: str = "openai/gpt-3.5-turbo"):
    """Create an OpenRouter LLM instance."""
    return ChatOpenAI(
        model=model,
        temperature=0,
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    )


async def test_simple_evaluation():
    """Test basic evaluation functionality."""

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in environment")
        return

    print("✅ OpenRouter API key found")

    # Create LLM
    llm = create_openrouter_llm("openai/gpt-3.5-turbo")
    print("✅ LLM created")

    # Test article
    article = MockArticle(
        title="Test Article",
        content="This is a complete article with substantial content. It contains multiple paragraphs and provides comprehensive information on the topic. The article flows naturally and concludes properly.",
        url="https://example.com/test",
    )

    # Test the prompt directly
    from src.hex_machina.enrichment.evaluation.langchain.prompts.evaluation_prompts import (
        ARTICLE_COMPLETENESS_EVALUATION_PROMPT,
    )

    prompt = ARTICLE_COMPLETENESS_EVALUATION_PROMPT.format(
        title=article.title, content=article.text_content, url=article.url
    )

    print("\n=== Testing LLM Response ===")
    print("Sending prompt to LLM...")

    try:
        response = await llm.ainvoke(prompt)
        print(f"✅ LLM Response received: {response.content[:200]}...")

        # Test parsing
        from src.hex_machina.enrichment.evaluation.langchain.output_parsers.evaluation_parsers import (
            ContentCompletenessOutputParser,
        )

        parser = ContentCompletenessOutputParser()
        result = parser.parse(response.content)

        print("✅ Parsed result:")
        print(f"  - Is Complete: {result.is_complete}")
        print(f"  - Detected Issues: {result.detected_issues}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return

    print("\n=== Testing Full Evaluator ===")

    try:
        from src.hex_machina.enrichment.evaluation.langchain.chains.evaluation_chains import (
            ContentCompletenessEvaluator,
        )

        evaluator = ContentCompletenessEvaluator(llm=llm, logger=logger)

        # Test different types of content
        test_cases = [
            (
                "Complete Article",
                "This is a complete article with substantial content. It contains multiple paragraphs and provides comprehensive information on the topic. The article flows naturally and concludes properly.",
            ),
            (
                "Paywall Article",
                "This article is behind a paywall. Please subscribe to continue reading. Premium content requires a subscription.",
            ),
            (
                "Anti-bot Page",
                "Please enable JavaScript to view this content. Access denied. Please complete the CAPTCHA to continue.",
            ),
        ]

        for title, content in test_cases:
            test_article = MockArticle(
                title=title,
                content=content,
                url=f"https://example.com/{title.lower().replace(' ', '-')}",
            )

            print(f"\n--- Testing: {title} ---")
            result = await evaluator.evaluate_article(test_article)

            print(f"  Is Complete: {result.is_complete}")
            print(f"  Issues: {result.detected_issues}")
            print(f"  Processing Time: {result.processing_time_seconds:.2f}s")

    except Exception as e:
        print(f"❌ Error with evaluator: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Main test function."""
    print("🧪 Testing ContentCompleteness Evaluation System")
    print("=" * 50)

    await test_simple_evaluation()

    print("\n" + "=" * 50)
    print("✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())
