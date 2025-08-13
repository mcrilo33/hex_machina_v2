#!/usr/bin/env python3
"""
Test script to generate datasets by running a simple task multiple times.

This script will:
1. Load the simple task configuration
2. Run the task with different inputs
3. Generate datasets for each step and the overall task
"""

import yaml
from dotenv import load_dotenv

from src.hex_machina.langchain_tasks.builder import TaskBuilder
from src.hex_machina.langchain_tasks.config.models import TaskConfig
from src.hex_machina.langchain_tasks.datasets import StepDatasetManager


def main():
    """Run the simple task multiple times to generate datasets."""
    print("🚀 Testing Dataset Generation with Simple Task")
    print("=" * 60)

    # Load environment variables
    load_dotenv()
    print("✅ Environment variables loaded")

    # Load the task configuration
    with open("test_simple_task_for_datasets.yaml", "r") as f:
        config_data = yaml.safe_load(f)

    # Parse into TaskConfig
    task_config = TaskConfig(**config_data)
    print(f"✅ Loaded task: {task_config.name}")
    print(f"✅ Steps: {len(task_config.steps)}")
    print(
        f"✅ Task-level dataset: {'✅ Enabled' if task_config.dataset else '❌ Disabled'}"
    )

    # Check step-level datasets
    for step in task_config.steps:
        dataset_status = "✅ Enabled" if step.dataset else "❌ Disabled"
        print(f"   - Step '{step.name}': {dataset_status}")

    # Initialize components
    print("\n🔧 Initializing components...")
    dataset_manager = StepDatasetManager()
    builder = TaskBuilder(dataset_manager=dataset_manager)

    # Test inputs
    test_inputs = [
        {"name": "Alice", "style": "formal"},
        {"name": "Bob", "style": "casual"},
        {"name": "Charlie", "style": "friendly"},
        {"name": "Diana", "style": "professional"},
    ]

    print(f"\n📝 Running task with {len(test_inputs)} different inputs...")

    # Run the task with each input
    for i, inputs in enumerate(test_inputs):
        print(f"\n--- Run {i+1}/{len(test_inputs)} ---")
        print(f"Input: {inputs}")

        try:
            # Execute the task with tracing and dataset generation
            result = builder.invoke_with_tracing(task_config, inputs)
            print("✅ Task completed successfully")
            print(f"Result: {str(result)[:100]}...")

        except Exception as e:
            print(f"❌ Task failed: {e}")
            continue

    # Generate grouped datasets
    print("\n📊 Generating grouped datasets...")
    try:
        summary = builder.generate_grouped_datasets(task_config)
        print("✅ Dataset generation completed!")
        print(f"Summary: {summary}")

    except Exception as e:
        print(f"❌ Dataset generation failed: {e}")

    print("\n🎉 Dataset generation test completed!")
    print("=" * 60)
    print("📋 Next steps:")
    print("   1. Check LangSmith for generated datasets")
    print("   2. Use these datasets for experiment evaluation")
    print("   3. Run experiments with different parameters")


if __name__ == "__main__":
    main()
