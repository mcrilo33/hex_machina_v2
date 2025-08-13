#!/usr/bin/env python3
"""
Test script to run experiments using existing datasets.

This script will:
1. Load the experiment configuration
2. Generate task variations
3. Execute experiments with different parameters
4. Generate new datasets for comparison
"""

import yaml
from dotenv import load_dotenv

from src.hex_machina.langchain_tasks.builder import TaskBuilder
from src.hex_machina.langchain_tasks.config.models import ExperimentConfig
from src.hex_machina.langchain_tasks.datasets import StepDatasetManager
from src.hex_machina.langchain_tasks.experiments import ExperimentRunner


def main():
    """Run experiments using existing datasets."""
    print("🚀 Testing Experiment Execution with Existing Datasets")
    print("=" * 70)

    # Load environment variables
    load_dotenv()
    print("✅ Environment variables loaded")

    # Load the experiment configuration
    with open("test_experiment_with_datasets.yaml", "r") as f:
        config_data = yaml.safe_load(f)

    # Parse into ExperimentConfig
    experiment_config = ExperimentConfig(**config_data)
    print(f"✅ Loaded experiment: {experiment_config.name}")
    print(f"✅ Description: {experiment_config.description}")
    print(f"✅ Task: {experiment_config.task.name}")
    print(f"✅ Steps: {len(experiment_config.task.steps)}")

    # Check for multiple values
    print("\n🔍 Checking for multiple values in steps:")
    for step in experiment_config.task.steps:
        multi_values = step.get_multi_value_fields()
        if multi_values:
            print(f"   - Step '{step.name}' has multiple values:")
            for field, values in multi_values.items():
                print(f"     * {field}: {values}")
        else:
            print(f"   - Step '{step.name}': No multiple values")

    # Generate task variations
    print("\n🧪 Generating task variations...")
    variations = experiment_config.generate_task_variations()
    print(f"✅ Generated {len(variations)} task variations")

    for i, variation in enumerate(variations):
        print(f"\n📋 Variation {i}:")
        print(f"   - Task: {variation.name}")
        print(f"   - Steps: {len(variation.steps)}")

        for step in variation.steps:
            if step.config:
                print(f"   - Step '{step.name}' config: {step.config}")

    # Initialize components
    print("\n🔧 Initializing components...")
    dataset_manager = StepDatasetManager()
    builder = TaskBuilder(dataset_manager=dataset_manager)
    experiment_runner = ExperimentRunner(
        task_builder=builder, dataset_manager=dataset_manager
    )

    # Test inputs for experiments
    test_inputs = [
        {"name": "Alice", "style": "formal"},
        {"name": "Bob", "style": "casual"},
    ]

    print(f"\n📝 Running experiments with {len(test_inputs)} inputs...")

    # Run the experiment
    try:
        experiment_results = experiment_runner.run_experiment(
            experiment_config=experiment_config,
            inputs=test_inputs[0],  # Use first input for now
        )

        print("✅ Experiment completed successfully!")
        print(f"   - Total variations: {experiment_results['total_variations']}")
        print(f"   - Variations executed: {len(experiment_results['variations'])}")
        print(f"   - Datasets created: {len(experiment_results['datasets_created'])}")

        # Show variation results
        for i, variation in enumerate(experiment_results["variations"]):
            status = "✅ Success" if variation["success"] else "❌ Failed"
            print(f"   - Variation {i}: {status}")
            if variation["success"]:
                print(f"     Result: {str(variation['result'])[:100]}...")
            else:
                print(f"     Error: {variation['error']}")

        # Show dataset information
        if experiment_results["datasets_created"]:
            print("\n📊 Datasets created:")
            for dataset_info in experiment_results["datasets_created"]:
                print(f"   - {dataset_info['name']} ({dataset_info['type']})")

    except Exception as e:
        print(f"❌ Experiment execution failed: {e}")
        import traceback

        traceback.print_exc()

    print("\n🎉 Experiment execution test completed!")
    print("=" * 70)
    print("📋 Next steps:")
    print("   1. Check LangSmith for new experiment datasets")
    print("   2. Compare results across different parameter combinations")
    print("   3. Run evaluations on the new datasets")


if __name__ == "__main__":
    main()
