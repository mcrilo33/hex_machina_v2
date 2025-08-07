#!/usr/bin/env python3
"""Test script for iterative dataset building workflow."""

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


async def create_test_source_dataset():
    """Create a test source dataset with various article types."""

    # Check API keys
    if not os.getenv("OPENROUTER_API_KEY") or not os.getenv("LANGSMITH_API_KEY"):
        print("❌ API keys not configured")
        return None

    from src.hex_machina.enrichment.evaluation.langsmith import (
        EvaluationDatasetManager,
        setup_langsmith_environment,
    )

    setup_langsmith_environment()
    dataset_manager = EvaluationDatasetManager(logger=logger)

    # Create test articles with various completeness levels
    test_articles = [
        # Complete articles (should be positive examples)
        MockArticle(
            title="Complete AI Research Paper",
            content="""This comprehensive research paper presents a novel approach to machine learning. 
            The study introduces a new neural network architecture that achieves state-of-the-art 
            performance on multiple benchmarks. Our methodology combines attention mechanisms with 
            novel training techniques, resulting in a 15% improvement over existing models. 
            The paper includes detailed experimental results, ablation studies, and theoretical 
            analysis. We also provide open-source implementation and extensive documentation. 
            Future work directions and potential applications are thoroughly discussed.""",
            url="https://example.com/complete-ai-paper",
            article_id="art_001",
        ),
        MockArticle(
            title="Full Technology Review",
            content="""This in-depth technology review covers the latest developments in artificial 
            intelligence and their impact on various industries. The article provides comprehensive 
            analysis of current trends, including large language models, computer vision advances, 
            and ethical considerations. We examine case studies from healthcare, finance, and 
            education sectors. The review includes expert interviews, statistical data, and 
            future predictions. Detailed comparisons between different approaches and technologies 
            are presented with clear recommendations for practitioners.""",
            url="https://example.com/tech-review",
            article_id="art_002",
        ),
        # Incomplete articles (should be negative examples)
        MockArticle(
            title="Paywall Article - Premium Content",
            content="""This article contains valuable insights about machine learning trends. 
            However, to continue reading this premium content, you need to subscribe to our 
            service. Subscribe now to access the full article and unlock exclusive content. 
            Premium subscribers get access to in-depth analysis, expert interviews, and 
            detailed case studies. Don't miss out on this important information. 
            Subscribe today and join thousands of professionals who trust our content.""",
            url="https://example.com/paywall-article",
            article_id="art_003",
        ),
        MockArticle(
            title="Anti-bot Page - Access Denied",
            content="""Please enable JavaScript to view this content. 
            Access denied. Please complete the CAPTCHA to continue. 
            We've detected unusual activity from your IP address. 
            To ensure you're human, please solve the following puzzle. 
            If you continue to see this message, please contact support.""",
            url="https://example.com/antibot-page",
            article_id="art_004",
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
            article_id="art_005",
        ),
        # Borderline cases (interesting for iteration)
        MockArticle(
            title="Medium Length Article",
            content="""This article provides a good overview of recent developments in AI. 
            It covers the main points about machine learning applications in business. 
            The content is informative and well-structured, though not as comprehensive 
            as a full research paper. It includes practical examples and basic explanations 
            suitable for a general audience. The article concludes with some recommendations 
            for getting started with AI implementation.""",
            url="https://example.com/medium-article",
            article_id="art_006",
        ),
        MockArticle(
            title="Short but Complete Article",
            content="""This is a concise but complete article about AI trends. 
            It covers the essential points clearly and provides actionable insights. 
            The content is well-written and informative, though brief. 
            It serves its purpose as a quick overview of the topic.""",
            url="https://example.com/short-complete",
            article_id="art_007",
        ),
    ]

    # Create ground truth data
    ground_truth_data = {
        "https://example.com/complete-ai-paper": {
            "is_complete": True,
            "detected_issues": ["no_issues"],
            "notes": "Comprehensive research paper",
        },
        "https://example.com/tech-review": {
            "is_complete": True,
            "detected_issues": ["no_issues"],
            "notes": "In-depth technology review",
        },
        "https://example.com/paywall-article": {
            "is_complete": False,
            "detected_issues": ["subscription_wall"],
            "notes": "Paywall blocking content",
        },
        "https://example.com/antibot-page": {
            "is_complete": False,
            "detected_issues": ["anti_bot_page"],
            "notes": "Anti-bot protection",
        },
        "https://example.com/truncated-article": {
            "is_complete": False,
            "detected_issues": ["truncated_content"],
            "notes": "Article ends with 'Read more'",
        },
        "https://example.com/medium-article": {
            "is_complete": True,
            "detected_issues": ["no_issues"],
            "notes": "Medium length but complete",
        },
        "https://example.com/short-complete": {
            "is_complete": True,
            "detected_issues": ["no_issues"],
            "notes": "Short but complete article",
        },
    }

    # Create dataset
    dataset_name = f"test-source-dataset-{int(asyncio.get_event_loop().time())}"
    dataset = dataset_manager.create_test_dataset_from_articles(
        articles=test_articles,
        dataset_name=dataset_name,
        ground_truth_data=ground_truth_data,
    )

    print(f"✅ Created source dataset: {dataset.name}")
    print(f"   Dataset ID: {dataset.id}")
    print(f"   Examples: {dataset.example_count}")

    return dataset.name


async def test_iterative_dataset_building():
    """Test the iterative dataset building workflow."""

    print("🧪 Testing Iterative Dataset Building Workflow")
    print("=" * 60)

    # Check API keys
    if not os.getenv("OPENROUTER_API_KEY") or not os.getenv("LANGSMITH_API_KEY"):
        print("❌ API keys not configured")
        return

    # Create test source dataset
    print("\n=== Creating Test Source Dataset ===")
    source_dataset_name = await create_test_source_dataset()
    if not source_dataset_name:
        print("❌ Failed to create source dataset")
        return

    # Setup workflow
    print("\n=== Setting Up Iterative Workflow ===")
    from src.hex_machina.enrichment.evaluation.langsmith.workflows.iterative_dataset_building import (
        run_iterative_dataset_building,
    )

    llm = create_openrouter_llm("openai/gpt-3.5-turbo")
    target_dataset_name = f"testset-1-{int(asyncio.get_event_loop().time())}"

    # Run iterative workflow
    print("\n=== Running Iterative Dataset Building ===")
    print(f"Source: {source_dataset_name}")
    print(f"Target: {target_dataset_name}")
    print(f"Model: {llm.model_name}")
    print("Prompt: v1.0")

    try:
        results = await run_iterative_dataset_building(
            source_dataset_name=source_dataset_name,
            target_dataset_name=target_dataset_name,
            llm=llm,
            prompt_version="v1.0",
            max_iterations=5,
            stability_threshold=0.8,
        )

        # Display results
        print("\n=== Workflow Results ===")
        print(f"✅ Workflow completed: {results['workflow_completed']}")
        print(f"📊 Iterations performed: {results['iterations_performed']}")
        print(f"🎯 Final stable: {results['final_stable']}")
        print(f"📈 Total positive examples: {results['total_positive_examples']}")

        print("\n=== Iteration History ===")
        for iter_data in results["iteration_history"]:
            print(f"Iteration {iter_data['iteration']}:")
            print(f"  - Evaluated: {iter_data['total_evaluated']} articles")
            print(f"  - New positives: {iter_data['new_positive_examples']}")
            print(f"  - Stability score: {iter_data['stability_score']:.3f}")

        print("\n=== Final Evaluation ===")
        final_eval = results["final_evaluation"]
        print(f"Total examples: {final_eval['total_examples']}")
        print(f"Complete examples: {final_eval['complete_examples']}")
        print(f"Incomplete examples: {final_eval['incomplete_examples']}")
        print(f"Success rate: {final_eval['success_rate']:.2%}")

        print("\n📊 View your results at: https://smith.langchain.com/")
        print(f"   Source Dataset: {source_dataset_name}")
        print(f"   Target Dataset: {target_dataset_name}")

    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        import traceback

        traceback.print_exc()


async def test_prompt_iteration():
    """Test iterating with different prompts."""

    print("\n🧪 Testing Prompt Iteration")
    print("=" * 40)

    # Check API keys
    if not os.getenv("OPENROUTER_API_KEY") or not os.getenv("LANGSMITH_API_KEY"):
        print("❌ API keys not configured")
        return

    # Create test source dataset
    source_dataset_name = await create_test_source_dataset()
    if not source_dataset_name:
        return

    from src.hex_machina.enrichment.evaluation.langsmith.workflows.iterative_dataset_building import (
        run_iterative_dataset_building,
    )

    llm = create_openrouter_llm("openai/gpt-3.5-turbo")

    # Test different prompt versions
    prompt_versions = ["v1.0", "v1.1", "v1.2"]

    for prompt_version in prompt_versions:
        print(f"\n--- Testing Prompt Version: {prompt_version} ---")

        target_dataset_name = (
            f"testset-1-{prompt_version}-{int(asyncio.get_event_loop().time())}"
        )

        try:
            results = await run_iterative_dataset_building(
                source_dataset_name=source_dataset_name,
                target_dataset_name=target_dataset_name,
                llm=llm,
                prompt_version=prompt_version,
                max_iterations=3,  # Shorter for testing
                stability_threshold=0.8,
            )

            print(
                f"  ✅ Completed with {results['total_positive_examples']} positive examples"
            )
            print(f"  📊 Iterations: {results['iterations_performed']}")
            print(f"  🎯 Stable: {results['final_stable']}")

        except Exception as e:
            print(f"  ❌ Failed: {e}")


async def main():
    """Main test function."""
    print("🧪 Testing Iterative Dataset Building Workflow")
    print("=" * 60)

    await test_iterative_dataset_building()
    await test_prompt_iteration()

    print("\n" + "=" * 60)
    print("✅ Iterative dataset building test completed!")
    print("\n📋 Next Steps:")
    print("1. Review the generated datasets in LangSmith")
    print("2. Manually validate positive examples in testset-1")
    print("3. Iterate on prompts based on results")
    print("4. Use the stable dataset for final evaluation")


if __name__ == "__main__":
    asyncio.run(main())
