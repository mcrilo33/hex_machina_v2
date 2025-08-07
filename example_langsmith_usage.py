#!/usr/bin/env python3
"""Example usage of LangSmith integration with real data."""

import asyncio
import logging
import os
import sys

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_with_real_data():
    """Example of using LangSmith with real scraped articles."""

    # Check if LangSmith is configured
    if not os.getenv("LANGSMITH_API_KEY"):
        print("⚠️  LangSmith not configured. Running without tracing.")
        print("   Add LANGSMITH_API_KEY to .env to enable full tracking.")

    # Setup LangSmith if available
    try:
        from src.hex_machina.enrichment.evaluation.langsmith import (
            EvaluationDatasetManager,
            EvaluationTracer,
            TracedContentCompletenessEvaluator,
            setup_langsmith_environment,
        )

        setup_langsmith_environment()
        langsmith_available = True
    except Exception as e:
        print(f"⚠️  LangSmith setup failed: {e}")
        langsmith_available = False

    # Create LLM
    from src.hex_machina.enrichment.llm.config import create_evaluation_llm

    llm = create_evaluation_llm("gpt-3.5-turbo")

    # Create base evaluator
    from src.hex_machina.enrichment.evaluation.langchain.chains.evaluation_chains import (
        ContentCompletenessEvaluator,
    )

    base_evaluator = ContentCompletenessEvaluator(llm=llm, logger=logger)

    # Setup tracing if available
    if langsmith_available:
        tracer = EvaluationTracer(logger=logger)
        evaluator = TracedContentCompletenessEvaluator(base_evaluator, tracer)

        # Start evaluation run
        tracer.start_evaluation_run(
            run_name="real-data-evaluation",
            model_name="openai/gpt-3.5-turbo",
            prompt_version="v1.0",
            metadata={
                "data_source": "scraped_articles",
                "evaluation_type": "content_completeness",
            },
        )
    else:
        evaluator = base_evaluator

    # Example: Load articles from your database
    # This is where you would integrate with your actual data source
    articles = await load_articles_from_database()

    if not articles:
        print("No articles found. Creating sample data...")
        articles = create_sample_articles()

    print(f"Evaluating {len(articles)} articles...")

    # Evaluate articles
    results = await evaluator.evaluate_articles(articles)

    # Analyze results
    complete_count = sum(1 for r in results if r.is_complete)
    incomplete_count = len(results) - complete_count

    print("\n=== Evaluation Results ===")
    print(f"Total Articles: {len(results)}")
    print(f"Complete: {complete_count} ({complete_count/len(results)*100:.1f}%)")
    print(f"Incomplete: {incomplete_count} ({incomplete_count/len(results)*100:.1f}%)")

    # Show some examples
    print("\n=== Sample Results ===")
    for i, result in enumerate(results[:5]):  # Show first 5
        print(f"{i+1}. {result.url}")
        print(f"   Complete: {result.is_complete}")
        print(f"   Issues: {result.detected_issues}")
        print(f"   Time: {result.processing_time_seconds:.2f}s")
        print()

    # If LangSmith is available, create dataset
    if langsmith_available:
        print("=== Creating LangSmith Dataset ===")
        dataset_manager = EvaluationDatasetManager(logger=logger)

        dataset = dataset_manager.create_test_dataset_from_articles(
            articles=articles, dataset_name="real-articles-evaluation"
        )

        print(f"✅ Dataset created: {dataset.name}")
        print("📊 View at: https://smith.langchain.com/")

    return results


async def load_articles_from_database():
    """Load articles from your database.

    This is where you would integrate with your actual data source.
    For now, we return an empty list to use sample data.
    """
    # TODO: Implement actual database integration
    # Example:
    # from src.hex_machina.storage.manager import StorageManager
    # storage = StorageManager()
    # articles = await storage.get_articles(limit=100)
    # return articles

    return []


def create_sample_articles():
    """Create sample articles for demonstration."""

    class MockArticle:
        def __init__(self, title: str, content: str, url: str, article_id: str = None):
            self.title = title
            self.text_content = content
            self.url = url
            self.id = article_id

    return [
        MockArticle(
            title="AI Breakthrough in Natural Language Processing",
            content="""Researchers at leading universities have made a significant breakthrough 
            in natural language processing. The new model, called GPT-5, demonstrates unprecedented 
            capabilities in understanding and generating human-like text. The study, published in 
            Nature, shows that the model achieves human-level performance on multiple benchmarks 
            including reading comprehension, text generation, and language translation. The research 
            team used innovative training techniques including reinforcement learning from human 
            feedback and advanced attention mechanisms. Results indicate a 25% improvement over 
            previous state-of-the-art models. This breakthrough has important implications for 
            artificial intelligence applications in healthcare, education, and business. The complete 
            methodology and detailed results are thoroughly documented in the research paper.""",
            url="https://example.com/ai-breakthrough-2024",
            article_id="art_001",
        ),
        MockArticle(
            title="Subscribe to Continue Reading - Premium Content",
            content="""This article contains exclusive insights about the future of machine learning. 
            Our expert analysis reveals the top trends that will shape the industry in 2024. 
            However, to continue reading this premium content, you need to subscribe to our 
            professional service. Subscribe now to access the full article and unlock exclusive 
            content including detailed case studies, expert interviews, and comprehensive analysis. 
            Premium subscribers get access to our entire library of in-depth articles, monthly 
            reports, and exclusive webinars. Don't miss out on this valuable information that 
            could transform your business strategy. Subscribe today and join thousands of 
            professionals who trust our content for their strategic decisions.""",
            url="https://example.com/premium-ml-trends",
            article_id="art_002",
        ),
        MockArticle(
            title="JavaScript Required - Please Enable JavaScript",
            content="""Please enable JavaScript to view this content. 
            Access denied. We've detected that JavaScript is disabled in your browser. 
            To ensure the best experience and access to our content, please enable JavaScript 
            and refresh the page. If you continue to see this message, please check your 
            browser settings or contact our support team for assistance. This security measure 
            helps protect our content and ensures proper functionality of our website.""",
            url="https://example.com/javascript-required",
            article_id="art_003",
        ),
    ]


async def example_model_comparison():
    """Example of comparing different models using LangSmith."""

    print("\n=== Model Comparison Example ===")

    # Check LangSmith availability
    if not os.getenv("LANGSMITH_API_KEY"):
        print("⚠️  LangSmith not configured. Model comparison will be limited.")
        return

    try:
        from src.hex_machina.enrichment.evaluation.langsmith import (
            EvaluationTracer,
            TracedContentCompletenessEvaluator,
            setup_langsmith_environment,
        )

        setup_langsmith_environment()
    except Exception as e:
        print(f"❌ LangSmith setup failed: {e}")
        return

    # Create test articles
    articles = create_sample_articles()

    # Models to compare
    models = [
        "openai/gpt-3.5-turbo",
        "anthropic/claude-3-haiku-20240307",
        "google/gemini-pro",
    ]

    results = {}

    for model in models:
        print(f"\n--- Testing {model} ---")

        try:
            # Create evaluator for this model
            from src.hex_machina.enrichment.evaluation.langchain.chains.evaluation_chains import (
                ContentCompletenessEvaluator,
            )
            from src.hex_machina.enrichment.llm.config import create_evaluation_llm

            llm = create_evaluation_llm(model)
            base_evaluator = ContentCompletenessEvaluator(llm=llm, logger=logger)

            # Setup tracing
            tracer = EvaluationTracer(logger=logger)
            evaluator = TracedContentCompletenessEvaluator(base_evaluator, tracer)

            # Start run
            run_name = f"model-comparison-{model.replace('/', '-')}"
            tracer.start_evaluation_run(run_name, model, "v1.0")

            # Evaluate
            start_time = asyncio.get_event_loop().time()
            model_results = await evaluator.evaluate_articles(articles)
            end_time = asyncio.get_event_loop().time()

            # Calculate metrics
            complete_count = sum(1 for r in model_results if r.is_complete)
            avg_time = sum(r.processing_time_seconds for r in model_results) / len(
                model_results
            )

            results[model] = {
                "complete_count": complete_count,
                "incomplete_count": len(model_results) - complete_count,
                "accuracy": complete_count / len(model_results),
                "avg_time": avg_time,
                "total_time": end_time - start_time,
            }

            print(f"  Complete: {complete_count}/{len(model_results)}")
            print(f"  Accuracy: {results[model]['accuracy']:.1%}")
            print(f"  Avg Time: {avg_time:.2f}s")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results[model] = {"error": str(e)}

    # Summary
    print("\n=== Model Comparison Summary ===")
    for model, result in results.items():
        if "error" in result:
            print(f"{model}: ❌ {result['error']}")
        else:
            print(
                f"{model}: {result['complete_count']}/{len(articles)} complete "
                f"({result['accuracy']:.1%}) in {result['avg_time']:.2f}s avg"
            )


async def main():
    """Main example function."""
    print("📊 LangSmith Integration Examples")
    print("=" * 50)

    # Example 1: Basic evaluation with real data
    await example_with_real_data()

    # Example 2: Model comparison
    await example_model_comparison()

    print("\n" + "=" * 50)
    print("✅ Examples completed!")
    print("\n💡 Tips:")
    print("- Add LANGSMITH_API_KEY to .env for full tracking")
    print("- View results at https://smith.langchain.com/")
    print("- Use datasets for ground truth collection")
    print("- Compare models systematically")


if __name__ == "__main__":
    asyncio.run(main())
