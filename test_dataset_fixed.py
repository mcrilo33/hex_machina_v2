#!/usr/bin/env python3
"""
Test script for the fixed dataset generation functionality.

This script tests that step-level examples are now properly created.
"""

import os
import sys

import yaml

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from hex_machina.langchain_tasks.builder import TaskBuilder
    from hex_machina.langchain_tasks.datasets import StepDatasetManager
    from hex_machina.langchain_tasks.registry import RunnableRegistry

    print("✅ Successfully imported all required modules")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def test_fixed_dataset_generation():
    """Test the fixed dataset generation functionality."""

    print("\n🧪 Testing Fixed Dataset Generation System")
    print("=" * 55)

    try:
        # Load environment variables
        from dotenv import load_dotenv

        load_dotenv()
        print("✅ Environment variables loaded")

        # Create components
        registry = RunnableRegistry()
        dataset_manager = StepDatasetManager()
        builder = TaskBuilder(registry=registry, dataset_manager=dataset_manager)

        print(f"✅ Created TaskBuilder with dataset manager: {builder}")

        # Load task configuration
        with open("test_task_config.yaml", "r") as file:
            config = yaml.safe_load(file)
        print(f"✅ Loaded task config: {config['name']}")

        # Show dataset configuration
        print("\n📋 Dataset Configuration:")
        for i, step in enumerate(config["steps"], 1):
            dataset_enabled = step.get("dataset", False)
            print(
                f"   Step {i}: {step['name']} - Dataset: {'✅ Enabled' if dataset_enabled else '❌ Disabled'}"
            )

        # Test input
        test_input = {"name": "David"}
        print(f"\n📥 Test input: {test_input}")

        # Execute with dataset generation
        print("\n🚀 Executing task with fixed dataset generation...")
        result = builder.invoke_with_tracing(config, test_input)

        print("✅ Task executed successfully!")
        print(f"📤 Result: {result}")

        # Show dataset generation summary
        print("\n📊 Dataset Generation Summary:")
        status = dataset_manager.get_current_status()
        for key, value in status.items():
            print(f"   {key}: {value}")

        # Get generator stats to see example counts
        generator_stats = dataset_manager.generator.get_dataset_stats()
        print("\n📈 Generator Statistics:")
        for key, value in generator_stats.items():
            if key == "example_counts":
                print(f"   {key}:")
                for dataset_name, count in value.items():
                    print(f"     {dataset_name}: {count} examples")
            else:
                print(f"   {key}: {value}")

        print("\n🎯 What to check in LangSmith:")
        print("1. Go to: https://smith.langchain.com/")
        print("2. Navigate to project: hex-machina-v2")
        print("3. Look for datasets:")
        print("   - simple_hello_task_generate_greeting_YYYYMMDD_HHMMSS")
        print("   - simple_hello_task_llm_response_YYYYMMDD_HHMMSS")
        print("4. Check that each dataset now has 1 example (not 0)")
        print("5. Verify examples have run_id metadata and step information")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_fixed_dataset_generation()

    if success:
        print("\n🎉 Fixed dataset generation test completed successfully!")
        print("Check LangSmith for the datasets with proper examples.")
    else:
        print("\n🔧 Test failed. Please check the error messages above.")
        sys.exit(1)
