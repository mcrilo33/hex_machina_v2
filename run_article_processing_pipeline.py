"""Demonstrate LangChain map-reduce pattern for processing articles individually with tracing."""

import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_core.runnables import RunnableLambda

from src.hex_machina.langchain_tasks.builder import TaskBuilder
from src.hex_machina.langchain_tasks.datasets import StepDatasetManager
from src.hex_machina.langchain_tasks.registry import RunnableRegistry
from src.hex_machina.langchain_tasks.runnables import (
    ArticleFetcher,
    ArticleProcessor,
    EnrichmentSaver,
)

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)


def create_article_processing_pipeline():
    """Create a LangChain pipeline that processes articles individually."""
    print("🚀 Creating LangChain Article Processing Pipeline\n")

    # Create registry and register our custom runnables
    registry = RunnableRegistry()
    registry.register("ArticleFetcher", ArticleFetcher)
    registry.register("ArticleProcessor", ArticleProcessor)
    registry.register("EnrichmentSaver", EnrichmentSaver)

    print("✅ Registered custom runnables:")
    available = registry.list_available_runnables()
    print(f"   Custom: {available['custom']}")

    # Create dataset manager
    dataset_manager = StepDatasetManager()

    # Create task builder
    builder = TaskBuilder(registry=registry, dataset_manager=dataset_manager)

    # Load task configuration
    task_config = {
        "name": "article_processing_pipeline",
        "description": "Demonstrates LangChain map-reduce pattern",
        "dataset": True,
        "steps": [
            {
                "name": "fetch_articles",
                "runnable": "ArticleFetcher",
                "dataset": True,
                "config": {"db_path": "storage/articles14.db", "filters": {"limit": 3}},
            },
            {
                "name": "process_articles_individually",
                "runnable": "ArticleProcessor",
                "dataset": True,
                "config": {"processor_type": "summarize", "summary_length": "short"},
            },
            {
                "name": "save_processed_results",
                "runnable": "EnrichmentSaver",
                "dataset": True,
                "config": {
                    "db_path": "storage/articles14.db",
                    "enrichment_type": "article_summary",
                    "input_mapping": "process_articles_individually.result",
                },
            },
        ],
    }

    print("\n🔧 Building task...")
    try:
        # Build the task
        task = builder.invoke(task_config)
        print("✅ Task built successfully!")

        # Execute the task with tracing
        print("\n🚀 Executing task with LangSmith tracing...")
        inputs = {"task_input": "Starting article processing pipeline"}

        result = builder.invoke_with_tracing(task_config, inputs)

        print("✅ Task executed successfully!")
        print(f"📊 Result type: {type(result)}")

        # Generate datasets
        print("\n📊 Generating datasets...")
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

    except Exception as e:
        print(f"❌ Task execution failed: {e}")
        import traceback

        traceback.print_exc()


def demonstrate_langchain_mapping():
    """Demonstrate the core LangChain mapping concept."""
    print("\n" + "=" * 60)
    print("🔍 Demonstrating LangChain Mapping Concept")
    print("=" * 60)

    # Create a simple mapping example

    # Simulate articles
    articles = [
        {"id": 1, "title": "AI Breakthrough", "content": "Machine learning advances"},
        {"id": 2, "title": "Business Strategy", "content": "Startup growth tactics"},
        {"id": 3, "title": "Tech Innovation", "content": "Future technology trends"},
    ]

    print(f"📚 Processing {len(articles)} articles individually...")

    # Create a processor that works on individual articles
    def process_article(article: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single article (this would be traced individually)."""
        return {
            "article_id": article["id"],
            "title": article["title"],
            "processed": True,
            "summary": f"Processed: {article['title']}",
        }

    # Use LangChain's mapping to process each article individually
    processor = RunnableLambda(process_article)

    # This is the key: map over each article individually
    # Each article gets its own execution trace in LangSmith
    results = []
    for i, article in enumerate(articles):
        print(f"  🔄 Processing article {i+1}: {article['title']}")
        result = processor.invoke({"article": article})
        results.append(result)
        print(f"     ✅ Result: {result['summary']}")

    print(f"\n🎯 All {len(articles)} articles processed individually!")
    print("   Each article gets its own trace in LangSmith")
    print("   This is the proper LangChain pattern for batch processing")


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

    # Demonstrate the concept first
    demonstrate_langchain_mapping()

    print("\n" + "=" * 60)

    # Run the actual pipeline
    create_article_processing_pipeline()
