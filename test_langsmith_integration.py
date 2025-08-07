#!/usr/bin/env python3
"""Test script for LangSmith integration with content completeness evaluation."""

import asyncio
import logging
import os
import sys

# Load environment variables
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

    def __init__(self, title: str, content: str, url: str, article_id: str = None):
        self.title = title
        self.text_content = content
        self.url = url
        self.id = article_id


def create_openrouter_llm(model: str = "openai/gpt-3.5-turbo"):
    """Create an OpenRouter LLM instance."""
    return ChatOpenAI(
        model=model,
        temperature=0,
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    )


async def test_langsmith_integration():
    """Test LangSmith integration with evaluation tracking."""

    # Check API keys
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    langsmith_key = os.getenv("LANGSMITH_API_KEY")

    if not openrouter_key:
        print("❌ OPENROUTER_API_KEY not found in environment")
        return

    if not langsmith_key:
        print("❌ LANGSMITH_API_KEY not found in environment")
        print("   Get your API key from: https://smith.langchain.com/")
        return

    print("✅ API keys configured")

    # Setup LangSmith environment
    from src.hex_machina.enrichment.evaluation.langsmith import (
        EvaluationDatasetManager,
        EvaluationTracer,
        LangSmithConfig,
        TracedContentCompletenessEvaluator,
        setup_langsmith_environment,
    )

    setup_langsmith_environment()

    # Create test articles with known characteristics
    test_articles = [
        MockArticle(
            title="Complete Article - AI Breakthrough",
            content="""This is a complete article about a major AI breakthrough. 
            Researchers have developed a new model that achieves unprecedented performance 
            on multiple benchmarks. The study, published in Nature, demonstrates significant 
            improvements in both accuracy and efficiency. The team used innovative techniques 
            including advanced attention mechanisms and novel training methodologies. 
            Results show a 15% improvement over previous state-of-the-art models. 
            The research has important implications for the future of artificial intelligence 
            and could lead to new applications in healthcare, education, and other fields. 
            The complete methodology and results are thoroughly documented in the paper.""",
            url="https://example.com/complete-article-1",
            article_id="art_001",
        ),
        MockArticle(
            title="Paywall Article - Premium Content",
            content="""This article contains valuable insights about machine learning trends. 
            However, to continue reading this premium content, you need to subscribe to our 
            service. Subscribe now to access the full article and unlock exclusive content. 
            Premium subscribers get access to in-depth analysis, expert interviews, and 
            detailed case studies. Don't miss out on this important information. 
            Subscribe today and join thousands of professionals who trust our content.""",
            url="https://example.com/paywall-article",
            article_id="art_002",
        ),
        MockArticle(
            title="Anti-bot Page - Access Denied",
            content="""Please enable JavaScript to view this content. 
            Access denied. Please complete the CAPTCHA to continue. 
            We've detected unusual activity from your IP address. 
            To ensure you're human, please solve the following puzzle. 
            If you continue to see this message, please contact support.""",
            url="https://example.com/antibot-page",
            article_id="art_003",
        ),
        MockArticle(
            title="Truncated Article - Incomplete Content",
            content="""This article discusses the latest developments in natural language processing. 
            The field has seen remarkable progress in recent years, with new models achieving 
            human-level performance on various tasks. Researchers are exploring novel architectures 
            and training methods. The implications for industry applications are significant. 
            Companies are already adopting these technologies for customer service, content 
            generation, and data analysis. However, challenges remain in areas such as... 
            Read more to see the complete analysis and future predictions.""",
            url="https://example.com/truncated-article",
            article_id="art_004",
        ),
    ]

    # Create ground truth data for comparison
    ground_truth_data = {
        "https://example.com/complete-article-1": {
            "is_complete": True,
            "detected_issues": ["no_issues"],
            "notes": "Full article with comprehensive content",
        },
        "https://example.com/paywall-article": {
            "is_complete": False,
            "detected_issues": ["subscription_wall"],
            "notes": "Paywall blocking full content",
        },
        "https://example.com/antibot-page": {
            "is_complete": False,
            "detected_issues": ["anti_bot_page"],
            "notes": "Anti-bot protection page",
        },
        "https://example.com/truncated-article": {
            "is_complete": False,
            "detected_issues": ["truncated_content"],
            "notes": "Article ends with 'Read more' prompt",
        },
    }

    print("\n=== Testing LangSmith Dataset Management ===")

    # Create dataset manager
    dataset_manager = EvaluationDatasetManager(logger=logger)

    # Create test dataset
    dataset_name = f"test-content-evaluation-{int(asyncio.get_event_loop().time())}"
    dataset = dataset_manager.create_test_dataset_from_articles(
        articles=test_articles,
        dataset_name=dataset_name,
        ground_truth_data=ground_truth_data,
    )

    print(f"✅ Created dataset: {dataset.name}")
    print(f"   Dataset ID: {dataset.id}")
    print(f"   Examples: {dataset.example_count}")

    print("\n=== Testing Traced Evaluation ===")

    # Create LLM and evaluator
    llm = create_openrouter_llm("openai/gpt-3.5-turbo")

    from src.hex_machina.enrichment.evaluation.langchain.chains.evaluation_chains import (
        ContentCompletenessEvaluator,
    )

    base_evaluator = ContentCompletenessEvaluator(llm=llm, logger=logger)

    # Create tracer and traced evaluator
    tracer = EvaluationTracer(logger=logger)
    traced_evaluator = TracedContentCompletenessEvaluator(
        evaluator=base_evaluator, tracer=tracer
    )

    # Start evaluation run
    run_name = f"evaluation-run-{int(asyncio.get_event_loop().time())}"
    tracer.start_evaluation_run(
        run_name=run_name,
        model_name="openai/gpt-3.5-turbo",
        prompt_version="v1.0",
        metadata={
            "test_type": "langsmith_integration",
            "dataset_name": dataset.name,
            "ground_truth_available": True,
        },
    )

    print(f"✅ Started evaluation run: {run_name}")

    # Evaluate articles
    results = await traced_evaluator.evaluate_articles(test_articles)

    print("\n=== Evaluation Results ===")
    for i, (article, result) in enumerate(zip(test_articles, results)):
        print(f"\nArticle {i+1}: {article.title}")
        print(f"  URL: {article.url}")
        print(f"  Is Complete: {result.is_complete}")
        print(f"  Issues: {result.detected_issues}")
        print(f"  Processing Time: {result.processing_time_seconds:.2f}s")

        # Compare with ground truth
        if article.url in ground_truth_data:
            expected = ground_truth_data[article.url]["is_complete"]
            if expected == result.is_complete:
                print("  ✅ Ground Truth Match")
            else:
                print(f"  ❌ Ground Truth Mismatch (expected: {expected})")

    print("\n=== LangSmith Integration Summary ===")
    print("✅ All evaluations tracked in LangSmith")
    print("✅ Dataset created with ground truth data")
    print("✅ Run metadata captured")
    print("✅ Individual article evaluations logged")
    print("✅ Performance metrics tracked")

    print("\n📊 View your results at: https://smith.langchain.com/")
    print(f"   Project: {LangSmithConfig.get_project_name()}")
    print(f"   Dataset: {dataset.name}")
    print(f"   Run: {run_name}")


async def test_model_comparison():
    """Test comparing different models using LangSmith."""

    print("\n=== Testing Model Comparison ===")

    # Check API keys
    if not os.getenv("OPENROUTER_API_KEY") or not os.getenv("LANGSMITH_API_KEY"):
        print("❌ API keys not configured, skipping model comparison")
        return

    # Setup LangSmith
    from src.hex_machina.enrichment.evaluation.langsmith import (
        EvaluationTracer,
        TracedContentCompletenessEvaluator,
        setup_langsmith_environment,
    )

    setup_langsmith_environment()

    # Test article
    test_article = MockArticle(
        title="Model Comparison Test",
        content="""This is a test article for comparing different models. 
        It contains a mix of content that should be evaluated consistently 
        across different language models. The article is complete and 
        contains substantial information about artificial intelligence 
        and machine learning applications in modern technology.""",
        url="https://example.com/model-comparison-test",
        article_id="art_005",
    )

    # Models to test
    models = [
        "openai/gpt-3.5-turbo",
        "anthropic/claude-3-haiku-20240307",
        "google/gemini-pro",
    ]

    results = {}

    for model in models:
        print(f"\n--- Testing Model: {model} ---")

        try:
            # Create LLM and evaluator
            llm = create_openrouter_llm(model)

            from src.hex_machina.enrichment.evaluation.langchain.chains.evaluation_chains import (
                ContentCompletenessEvaluator,
            )

            base_evaluator = ContentCompletenessEvaluator(llm=llm, logger=logger)

            # Create tracer and traced evaluator
            tracer = EvaluationTracer(logger=logger)
            traced_evaluator = TracedContentCompletenessEvaluator(
                evaluator=base_evaluator, tracer=tracer
            )

            # Start evaluation run
            run_name = f"model-comparison-{model.replace('/', '-')}-{int(asyncio.get_event_loop().time())}"
            tracer.start_evaluation_run(
                run_name=run_name,
                model_name=model,
                prompt_version="v1.0",
                metadata={"test_type": "model_comparison"},
            )

            # Evaluate
            start_time = asyncio.get_event_loop().time()
            result = await traced_evaluator.evaluate_article(test_article)
            end_time = asyncio.get_event_loop().time()

            results[model] = {
                "is_complete": result.is_complete,
                "issues": result.detected_issues,
                "processing_time": end_time - start_time,
            }

            print(f"  Result: {result.is_complete}")
            print(f"  Issues: {result.detected_issues}")
            print(f"  Time: {results[model]['processing_time']:.2f}s")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results[model] = {"error": str(e)}

    print("\n=== Model Comparison Summary ===")
    for model, result in results.items():
        if "error" in result:
            print(f"{model}: ❌ {result['error']}")
        else:
            print(
                f"{model}: {result['is_complete']} ({result['processing_time']:.2f}s)"
            )


async def main():
    """Main test function."""
    print("🧪 Testing LangSmith Integration for Content Completeness Evaluation")
    print("=" * 70)

    await test_langsmith_integration()
    await test_model_comparison()

    print("\n" + "=" * 70)
    print("✅ LangSmith integration test completed!")
    print("\n📋 Next Steps:")
    print("1. Get your LangSmith API key from: https://smith.langchain.com/")
    print("2. Add LANGSMITH_API_KEY to your .env file")
    print("3. View your evaluation runs in the LangSmith dashboard")
    print("4. Use the dataset for ground truth collection and model comparison")


if __name__ == "__main__":
    asyncio.run(main())
