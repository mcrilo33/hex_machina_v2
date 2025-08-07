#!/usr/bin/env python3
"""Iterative dataset building workflow using LangSmith feedback."""

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


async def run_iterative_workflow():
    """Run the complete iterative dataset building workflow."""

    print("🔄 Iterative Dataset Building Workflow")
    print("=" * 50)

    # Check API keys
    if not os.getenv("OPENROUTER_API_KEY") or not os.getenv("LANGSMITH_API_KEY"):
        print("❌ API keys not configured")
        print(
            "   Please set OPENROUTER_API_KEY and LANGSMITH_API_KEY in your .env file"
        )
        return

    # Setup LangSmith
    from src.hex_machina.enrichment.evaluation.langsmith import (
        EvaluationDatasetManager,
        setup_langsmith_environment,
    )
    from src.hex_machina.enrichment.evaluation.langsmith.utils.dataset_naming import (
        DatasetNamingConvention,
    )
    from src.hex_machina.enrichment.evaluation.langsmith.workflows.iterative_builder import (
        IterativeDatasetBuilder,
    )

    setup_langsmith_environment()

    # Initialize components
    dataset_manager = EvaluationDatasetManager(logger=logger)
    iterative_builder = IterativeDatasetBuilder(logger=logger)

    # Step 1: List available datasets
    print("\n📋 Available Datasets:")
    print("-" * 30)

    datasets = dataset_manager.list_datasets()
    if not datasets:
        print("❌ No datasets found. Please create a source dataset first.")
        print("   Run: python create_first_dataset.py")
        return

    print("Available datasets:")
    for i, dataset in enumerate(datasets, 1):
        parsed = DatasetNamingConvention.parse_dataset_name(dataset.name)
        dataset_type = parsed.get("dataset_type", "unknown")
        print(f"   {i}. {dataset.name} ({dataset_type})")

    # Step 2: Select source dataset
    print("\n🎯 Step 1: Select Source Dataset")
    print("-" * 30)

    source_dataset_name = input("Enter source dataset name: ").strip()
    if not source_dataset_name:
        print("❌ Source dataset name is required")
        return

    # Verify dataset exists
    source_dataset = dataset_manager.get_dataset(source_dataset_name)
    if not source_dataset:
        print(f"❌ Dataset not found: {source_dataset_name}")
        return

    print(f"✅ Selected source dataset: {source_dataset_name}")

    # Step 3: Configure iterative build
    print("\n🔄 Step 2: Configure Iterative Build")
    print("-" * 30)

    content_category = input("Enter content category (e.g., 'ai_news'): ").strip()
    if not content_category:
        content_category = "ai_news"

    prompt_version = input("Enter prompt version (e.g., 'v1_0'): ").strip()
    if not prompt_version:
        prompt_version = "v1_0"

    iteration = input("Enter iteration number (or press Enter for auto): ").strip()
    if iteration:
        try:
            iteration = int(iteration)
        except ValueError:
            print("❌ Iteration must be a number")
            return
    else:
        iteration = None

    # Step 4: Build iterative dataset
    print("\n🏗️  Step 3: Building Iterative Dataset")
    print("-" * 30)

    try:
        iterative_dataset_name = await iterative_builder.build_iterative_dataset(
            source_dataset_name=source_dataset_name,
            content_category=content_category,
            prompt_version=prompt_version,
            iteration=iteration,
        )

        print(f"✅ Created iterative dataset: {iterative_dataset_name}")

    except Exception as e:
        print(f"❌ Failed to build iterative dataset: {e}")
        return

    # Step 5: Manual review instructions
    print("\n👀 Step 4: Manual Review Required")
    print("-" * 30)
    print("Now you need to manually review and correct the dataset in LangSmith:")
    print("1. Go to: https://smith.langchain.com/")
    print(f"2. Find dataset: {iterative_dataset_name}")
    print("3. Review articles marked as 'requires_manual_review'")
    print("4. Add feedback and corrections")
    print("5. Mark articles as 'human_labeled: true'")

    # Step 6: Create curated dataset (optional)
    print("\n✨ Step 5: Create Curated Dataset (Optional)")
    print("-" * 30)

    create_curated = (
        input("Create curated dataset from high-confidence examples? (y/n): ")
        .strip()
        .lower()
    )

    if create_curated == "y":
        try:
            curation_type = input(
                "Enter curation type (e.g., 'validated', 'expert_reviewed'): "
            ).strip()
            if not curation_type:
                curation_type = "validated"

            curated_dataset_name = await iterative_builder.create_curated_dataset(
                iterative_dataset_name=iterative_dataset_name,
                content_category=content_category,
                curation_type=curation_type,
                min_confidence="high",
            )

            print(f"✅ Created curated dataset: {curated_dataset_name}")

        except Exception as e:
            print(f"❌ Failed to create curated dataset: {e}")

    # Step 7: Model evaluation (optional)
    print("\n🤖 Step 6: Model Evaluation (Optional)")
    print("-" * 30)

    run_evaluation = (
        input("Run model evaluation on the dataset? (y/n): ").strip().lower()
    )

    if run_evaluation == "y":
        await run_model_evaluation(iterative_dataset_name, prompt_version)

    print("\n" + "=" * 50)
    print("✅ Iterative workflow completed!")
    print("\n📊 View your datasets at: https://smith.langchain.com/")
    print(f"   Source: {source_dataset_name}")
    print(f"   Iterative: {iterative_dataset_name}")


async def run_model_evaluation(dataset_name: str, prompt_version: str):
    """Run model evaluation on the dataset."""

    print(f"\n🤖 Evaluating models on {dataset_name}")

    # Get models to evaluate
    models_input = input(
        "Enter models to compare (comma-separated, e.g., 'gpt-3.5-turbo,claude-3-haiku'): "
    ).strip()
    if not models_input:
        models = ["openai/gpt-3.5-turbo", "anthropic/claude-3-haiku-20240307"]
    else:
        models = [model.strip() for model in models_input.split(",")]

    # Create evaluator factory
    def create_evaluator(model_name: str):
        from langchain_openai import ChatOpenAI

        from src.hex_machina.enrichment.evaluation.langchain.chains.evaluation_chains import (
            ContentCompletenessEvaluator,
        )

        llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        )

        return ContentCompletenessEvaluator(llm=llm, logger=logger)

    # Run comparison
    from src.hex_machina.enrichment.evaluation.langsmith.workflows.iterative_builder import (
        IterativeDatasetBuilder,
    )

    iterative_builder = IterativeDatasetBuilder(logger=logger)

    try:
        results = await iterative_builder.compare_models_on_dataset(
            dataset_name=dataset_name,
            models=models,
            prompt_version=prompt_version,
            evaluator_factory=create_evaluator,
        )

        # Display results
        print("\n📊 Model Comparison Results:")
        print("-" * 40)

        for model_name, result in results.items():
            if "error" in result:
                print(f"{model_name}: ❌ {result['error']}")
            else:
                accuracy = result["accuracy"]
                avg_time = result["avg_time"]
                print(f"{model_name}: {accuracy:.1%} accuracy, {avg_time:.2f}s avg")

    except Exception as e:
        print(f"❌ Model evaluation failed: {e}")


async def show_workflow_status():
    """Show the current status of the iterative workflow."""

    print("📊 Iterative Workflow Status")
    print("=" * 40)

    # Setup LangSmith
    from src.hex_machina.enrichment.evaluation.langsmith import (
        EvaluationDatasetManager,
        setup_langsmith_environment,
    )
    from src.hex_machina.enrichment.evaluation.langsmith.utils.dataset_naming import (
        DatasetNamingConvention,
    )

    setup_langsmith_environment()
    dataset_manager = EvaluationDatasetManager(logger=logger)

    # Get all datasets
    datasets = dataset_manager.list_datasets()

    if not datasets:
        print("❌ No datasets found")
        return

    # Group by type
    dataset_groups = {}
    for dataset in datasets:
        parsed = DatasetNamingConvention.parse_dataset_name(dataset.name)
        dataset_type = parsed.get("dataset_type", "unknown")

        if dataset_type not in dataset_groups:
            dataset_groups[dataset_type] = []
        dataset_groups[dataset_type].append(dataset)

    # Display status
    for dataset_type, type_datasets in dataset_groups.items():
        print(f"\n📁 {dataset_type.title()} Datasets ({len(type_datasets)}):")
        for dataset in type_datasets:
            parsed = DatasetNamingConvention.parse_dataset_name(dataset.name)
            content_category = parsed.get("content_category", "unknown")
            version = parsed.get("version", "")

            print(f"   • {dataset.name}")
            print(f"     Content: {content_category}")
            if version:
                print(f"     Version: {version}")
            print(f"     Examples: {dataset.example_count}")

    print("\n📊 View all datasets at: https://smith.langchain.com/")


async def main():
    """Main function."""
    print("🔄 LangSmith Iterative Dataset Building")
    print("=" * 50)

    # Show available options
    print("\nAvailable actions:")
    print("1. Run iterative workflow")
    print("2. Show workflow status")
    print("3. Exit")

    choice = input("\nSelect action (1-3): ").strip()

    if choice == "1":
        await run_iterative_workflow()
    elif choice == "2":
        await show_workflow_status()
    elif choice == "3":
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
