#!/usr/bin/env python3
"""
Test script for real step input/output capture.

This script tests that we now capture actual step execution data
instead of placeholder inputs/outputs.
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


def test_real_step_capture():
    """Test the real step input/output capture functionality."""

    print("\n🧪 Testing Real Step Input/Output Capture")
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
        test_input = {"name": "Emma"}
        print(f"\n📥 Test input: {test_input}")

        # Execute with enhanced dataset generation
        print("\n🚀 Executing task with real step capture...")
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
        print("3. Look for the latest datasets")
        print("4. Check that examples now have REAL inputs/outputs:")
        print("   - Step 1 (generate_greeting): Input should be {'name': 'Emma'}")
        print("   - Step 1: Output should be the actual prompt template result")
        print("   - Step 2 (llm_response): Input should be the prompt from step 1")
        print("   - Step 2: Output should be the actual LLM response")
        print("5. Verify metadata shows 'data_source': 'captured_execution'")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_real_step_capture()

    if success:
        print("\n🎉 Real step capture test completed successfully!")
        print("Check LangSmith for datasets with real execution data.")
    else:
        print("\n🔧 Test failed. Please check the error messages above.")
        sys.exit(1)
