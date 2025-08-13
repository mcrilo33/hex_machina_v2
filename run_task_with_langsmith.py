"""Run the custom runnables task with LangSmith tracing and dataset generation."""

import logging
import os

from dotenv import load_dotenv

from src.hex_machina.langchain_tasks.builder import TaskBuilder
from src.hex_machina.langchain_tasks.datasets import StepDatasetManager
from src.hex_machina.langchain_tasks.registry import RunnableRegistry
from src.hex_machina.langchain_tasks.runnables import (
    ArticleFetcher,
    EnrichmentSaver,
    MockKeywordExtractor,
    MockSummarizer,
)

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)


def run_task_with_langsmith():
    """Run the task with LangSmith tracing and dataset generation."""
    print("🚀 Running Custom Runnables Task with LangSmith Tracing\n")

    # Create registry and register our custom runnables
    registry = RunnableRegistry()
    registry.register("ArticleFetcher", ArticleFetcher)
    registry.register("EnrichmentSaver", EnrichmentSaver)
    registry.register("MockSummarizer", MockSummarizer)
    registry.register("MockKeywordExtractor", MockKeywordExtractor)

    print("✅ Registered custom runnables:")
    available = registry.list_available_runnables()
    print(f"   Custom: {available['custom']}")
    print(f"   Built-in: {available['builtin']}")

    # Create dataset manager
    dataset_manager = StepDatasetManager()

    # Create task builder
    builder = TaskBuilder(registry=registry, dataset_manager=dataset_manager)

    # Load task configuration
    task_config = {
        "name": "test_custom_runnables",
        "description": "Test task with custom database runnables",
        "dataset": True,
        "steps": [
            {
                "name": "fetch_sample_articles",
                "runnable": "ArticleFetcher",
                "dataset": True,
                "config": {"db_path": "storage/articles14.db", "filters": {"limit": 2}},
            },
            {
                "name": "generate_article_summary",
                "runnable": "MockSummarizer",
                "dataset": True,
                "config": {"summary_length": "short"},
            },
            {
                "name": "save_summaries",
                "runnable": "EnrichmentSaver",
                "dataset": True,
                "config": {
                    "db_path": "storage/articles14.db",
                    "enrichment_type": "article_summary",
                    "input_mapping": "generate_article_summary.summary",
                },
            },
        ],
    }

    print("\n🔧 Building task...")
    try:
        # Build the task
        task = builder.invoke(task_config)
        print("✅ Task built successfully!")

        # Execute the task with tracing using TaskBuilder's built-in tracing
        print("\n🚀 Executing task with LangSmith tracing...")
        inputs = {"task_input": "Starting custom runnables task"}

        # Use TaskBuilder's invoke_with_tracing method for proper LangSmith integration
        result = builder.invoke_with_tracing(task_config, inputs)

        print("✅ Task executed successfully!")
        print(f"📊 Result type: {type(result)}")

        # Generate datasets (this should now work since we used invoke_with_tracing)
        print("\n📊 Generating datasets...")

        # Convert dict to TaskConfig for dataset generation
        from src.hex_machina.langchain_tasks.builder import TaskConfig

        task_config_obj = TaskConfig(**task_config)
        builder.generate_grouped_datasets(task_config_obj)

        print("✅ Datasets generated!")

        # Show current status
        status = dataset_manager.get_current_status()
        print("\n📈 Dataset Status:")
        print(f"   Current run ID: {status.get('current_run_id', 'N/A')}")
        print(f"   Current task: {status.get('current_task_name', 'N/A')}")
        print(f"   Step datasets: {status.get('step_datasets', {})}")
        print(f"   Task dataset: {status.get('task_dataset', 'N/A')}")

    except Exception as e:
        print(f"❌ Task execution failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Check environment variables
    print("🔍 Checking LangSmith environment...")
    langsmith_v2 = os.getenv("LANGCHAIN_TRACING_V2")
    langsmith_endpoint = os.getenv("LANGCHAIN_ENDPOINT")
    langsmith_project = os.getenv("LANGCHAIN_PROJECT")

    print(f"   LANGCHAIN_TRACING_V2: {langsmith_v2}")
    print(f"   LANGCHAIN_ENDPOINT: {langsmith_endpoint}")
    print(f"   LANGCHAIN_PROJECT: {langsmith_project}")

    if not all([langsmith_v2, langsmith_endpoint, langsmith_project]):
        print("⚠️  Warning: Some LangSmith environment variables are missing!")
        print("   This may affect tracing and dataset generation.")

    print("\n" + "=" * 60)

    # Run the task
    run_task_with_langsmith()
