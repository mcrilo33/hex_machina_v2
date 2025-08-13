#!/usr/bin/env python3
"""
Test script for LLM article processing with PromptTemplate and ChatOpenAI.
Tests the map-reduce pattern with real LangChain runnables.
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment variables")

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from hex_machina.langchain_tasks.builder import TaskBuilder, TaskConfig
from hex_machina.langchain_tasks.datasets.generator import DatasetGenerator
from hex_machina.langchain_tasks.datasets.step_manager import StepDatasetManager
from hex_machina.langchain_tasks.registry import RunnableRegistry


def check_langsmith_environment():
    """Check if LangSmith environment is properly configured."""
    print("🔍 Checking LangSmith environment...")

    required_vars = [
        "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_ENDPOINT",
        "LANGCHAIN_API_KEY",
        "LANGCHAIN_PROJECT",
    ]

    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   {var}: {value}")
        else:
            print(f"   {var}: NOT SET")

    print()


def main():
    """Main test function."""
    print("=" * 60)
    print("🚀 Testing LLM Article Processing with Map-Reduce Pattern")
    print("=" * 60)

    # Check environment
    check_langsmith_environment()

    # Initialize components
    print("🔧 Initializing components...")

    # Initialize registry with built-in LangChain runnables
    registry = RunnableRegistry()
    print("✅ RunnableRegistry initialized")

    # Register custom runnables
    from hex_machina.langchain_tasks.runnables import ArticleFetcher, EnrichmentSaver

    registry.register("ArticleFetcher", ArticleFetcher)
    registry.register("EnrichmentSaver", EnrichmentSaver)
    print("✅ Custom runnables registered")

    # Show available runnables
    available = registry.list_available_runnables()
    print("📋 Available runnables:")
    print(f"   Custom: {available['custom']}")
    print(f"   Built-in: {available['builtin']}")

    # Initialize dataset components
    dataset_generator = DatasetGenerator()
    step_manager = StepDatasetManager()
    print("✅ Dataset components initialized")

    # Initialize TaskBuilder
    builder = TaskBuilder(registry, step_manager)
    print("✅ TaskBuilder initialized")

    # Load task configuration
    config_path = "test_article_processing_task.yaml"
    print(f"\n📋 Loading task configuration from: {config_path}")

    try:
        import yaml

        with open(config_path, "r") as f:
            task_config = yaml.safe_load(f)
        print("✅ Task configuration loaded")
    except Exception as e:
        print(f"❌ Failed to load task configuration: {e}")
        return

    # Build the task
    print("\n🔧 Building task...")
    try:
        task = builder.build_from_yaml(task_config)
        print("✅ Task built successfully!")
    except Exception as e:
        print(f"❌ Task building failed: {e}")
        return

    # Execute the task
    print("\n🚀 Executing task with LangSmith tracing...")
    try:
        # For ArticleFetcher, we don't need inputs since it fetches from database
        result = builder.invoke_with_tracing(task_config, {})
        print("✅ Task executed successfully!")
        print(f"📊 Result type: {type(result)}")
        print(f"📊 Result: {result}")
    except Exception as e:
        print(f"❌ Task execution failed: {e}")
        return

    # Datasets are now generated automatically during execution
    print("\n📊 Dataset generation...")
    print(
        "✅ Basic step datasets created - will be populated with trace data from LangSmith!"
    )

    # Now populate the datasets with actual trace data
    print("\n🔍 Populating datasets with LangSmith trace data...")
    try:
        # Convert dict to TaskConfig if needed
        if isinstance(task_config, dict):
            task_config_obj = TaskConfig(**task_config)
        else:
            task_config_obj = task_config

        # Generate grouped datasets from traces
        datasets = builder.generate_grouped_datasets(task_config_obj)
        print("✅ Datasets populated with trace data!")
        print(f"📈 Generated {len(datasets)} datasets")
    except Exception as e:
        print(f"❌ Dataset population failed: {e}")

    print("\n🎉 Test completed successfully!")
    print("\n📋 What you should see in LangSmith:")
    print("   1. One trace: 'test_llm_article_processing'")
    print("   2. One trace: 'save_all_enrichments_in_batch'")
    print("   3. Individual traces for each article processing")
    print("   4. NO individual EnrichmentSaver traces (batch operation)")
    print("\n📊 What you should see in LangSmith Datasets:")
    print("   1. Task-level dataset: 'test_llm_article_processing'")
    print("   2. Step-level datasets (now populated with trace data):")
    print("      - 'generate_article_summary' (with 2 examples - one per article)")
    print("      - 'llm_response' (with 2 examples - one per article)")
    print("   3. Note: Fetcher and Saver datasets are disabled")
    print(
        "\n💡 Each step dataset now contains the actual input/output data from LangSmith traces"
    )


if __name__ == "__main__":
    main()
