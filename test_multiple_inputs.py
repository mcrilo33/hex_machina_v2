#!/usr/bin/env python3
"""
Test script to verify multiple input handling and trace grouping.
This will test if the system can properly group multiple traces for each step.
"""

import os
import sys

import yaml
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from hex_machina.langchain_tasks.builder import TaskBuilder
from hex_machina.langchain_tasks.datasets import StepDatasetManager


def main():
    """Test multiple inputs with the same task configuration."""
    print("🧪 Testing Multiple Inputs and Trace Grouping")
    print("=" * 60)

    # Load environment variables
    load_dotenv()
    print("✅ Environment variables loaded")

    # Create TaskBuilder with dataset manager
    dataset_manager = StepDatasetManager()
    builder = TaskBuilder(dataset_manager=dataset_manager)
    print(f"✅ Created TaskBuilder: {builder}")
    print(f"✅ Dataset manager: {builder.dataset_manager}")

    # Load task config
    config_path = "test_task_config.yaml"
    with open(config_path, "r") as f:
        config_dict = yaml.safe_load(f)

    # Convert to TaskConfig object
    from hex_machina.langchain_tasks.builder import TaskConfig

    config = TaskConfig(**config_dict)
    print(f"✅ Loaded task config: {config.name}")

    # Print dataset configuration
    print("\n📋 Dataset Configuration:")
    for i, step in enumerate(config.steps, 1):
        status = "✅ Enabled" if step.dataset else "❌ Disabled"
        print(f"   Step {i}: {step.name} - Dataset: {status}")

    # Print task-level dataset configuration
    task_dataset_status = "✅ Enabled" if config.dataset else "❌ Disabled"
    print(f"   Task-level Dataset: {task_dataset_status}")

    # Define multiple test inputs
    test_inputs = [
        {"name": "Alice"},
        {"name": "Bob"},
        {"name": "Charlie"},
        {"name": "Diana"},
    ]

    print(f"\n📥 Test inputs: {len(test_inputs)} different names")
    for i, input_data in enumerate(test_inputs, 1):
        print(f"   Input {i}: {input_data}")

    # Execute task with each input (but don't generate datasets yet)
    print(f"\n🚀 Executing task with {len(test_inputs)} different inputs...")
    print("   (Datasets will be generated after all executions complete)")

    execution_results = []
    for i, input_data in enumerate(test_inputs, 1):
        print(f"\n--- Execution {i}/{len(test_inputs)} ---")
        print(f"Input: {input_data}")

        try:
            print("   Executing task...")
            # Execute the task with tracing (traces are stored for later grouping)
            result = builder.invoke_with_tracing(config, input_data)
            print(f"   ✅ Success! Result: {str(result)[:100]}...")
            execution_results.append(
                {"input": input_data, "result": result, "success": True}
            )

        except Exception as e:
            print(f"   ❌ Failed: {e}")
            import traceback

            traceback.print_exc()
            execution_results.append(
                {"input": input_data, "result": None, "success": False}
            )
            continue

    # Show execution summary
    print("\n📊 Execution Summary:")
    successful_executions = [r for r in execution_results if r["success"]]
    print(f"   Total executions: {len(execution_results)}")
    print(f"   Successful: {len(successful_executions)}")
    print(f"   Failed: {len(execution_results) - len(successful_executions)}")

    # Now generate grouped datasets from all traces
    if successful_executions:
        print("\n🔗 Generating Grouped Datasets...")
        print("   Gathering all traces and grouping examples by step...")

        try:
            summary = builder.generate_grouped_datasets(config)

            if summary:
                print("\n📈 Grouped Dataset Summary:")
                print(f"   Total datasets: {summary.get('total_datasets', 0)}")
                print(f"   Dataset names: {summary.get('dataset_names', [])}")

                example_counts = summary.get("example_counts", {})
                if example_counts:
                    print("   Example counts:")
                    for dataset_name, count in example_counts.items():
                        print(f"     {dataset_name}: {count} examples")

                print("\n✅ Grouped datasets generated successfully!")
            else:
                print("\n❌ Failed to generate grouped datasets")

        except Exception as e:
            print(f"\n❌ Error generating grouped datasets: {e}")
            import traceback

            traceback.print_exc()

    print("\n🎉 Multiple input test completed!")
    print(f"Executed task {len(test_inputs)} times with different inputs.")
    print("\n🎯 What to check in LangSmith:")
    print("1. Go to: https://smith.langchain.com/")
    print("2. Navigate to project: hex-machina-v2")
    print("3. Look for the latest datasets")
    print("4. Check that each step dataset now has 4 examples:")
    print("   - Step 1 (generate_greeting): 4 examples with different names")
    print("   - Step 2 (llm_response): 4 examples with different prompts/responses")
    print("5. Verify that examples are properly grouped by run_id")
    print(
        "6. Check that examples are grouped into shared datasets (not separate datasets per execution)"
    )


if __name__ == "__main__":
    main()
