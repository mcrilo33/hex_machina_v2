#!/usr/bin/env python3
"""
Test script for the task variation system with evaluation.

This script demonstrates how to:
1. Load experiment configuration with task variations from YAML
2. Generate multiple task variations based on multiple values
3. Run evaluations on existing datasets for each variation
4. Integrate with LangSmith for comprehensive evaluation
"""

import yaml
from dotenv import load_dotenv

from src.hex_machina.langchain_tasks.experiments import (
    ExperimentConfiguration,
    run_yaml_experiments_sync,
)


def main():
    """Test the task variation system with evaluation."""
    print("🚀 Testing Task Variation System with Evaluation")
    print("=" * 70)

    # Load environment variables
    load_dotenv()
    print("✅ Environment variables loaded")

    # Load the experiment configuration
    try:
        with open("test_experiment_config_with_variations.yaml", "r") as f:
            config_data = yaml.safe_load(f)
        print("✅ YAML configuration loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load YAML configuration: {e}")
        return

    # Parse into ExperimentConfiguration
    try:
        experiment_config = ExperimentConfiguration(**config_data)
        print(f"✅ Configuration parsed successfully: {experiment_config.name}")
        print(f"✅ Description: {experiment_config.description}")
    except Exception as e:
        print(f"❌ Failed to parse configuration: {e}")
        import traceback

        traceback.print_exc()
        return

    # Display configuration details
    print("\n📋 Configuration Details:")
    print(f"   - Name: {experiment_config.name}")
    print(f"   - Description: {experiment_config.description}")
    print(f"   - Settings prefix: {experiment_config.settings.experiment_prefix}")
    print(f"   - Save results: {experiment_config.settings.save_results}")

    # Check for multiple values in task configuration
    print("\n🔍 Task Configuration Analysis:")
    print(f"   - Task name: {experiment_config.task.name}")
    print(f"   - Task description: {experiment_config.task.description}")
    print(f"   - Steps: {len(experiment_config.task.steps)}")

    for step in experiment_config.task.steps:
        print(f"   - Step '{step.name}':")
        print(f"     Runnable: {step.runnable}")
        print(f"     Dataset: {step.dataset}")
        if step.config:
            multi_values = step.get_multi_value_fields()
            if multi_values:
                print("     Multiple values detected:")
                for field, values in multi_values.items():
                    print(f"       * {field}: {values}")
            else:
                print(f"     Config: {step.config}")

    # Generate and display task variations
    print("\n🧪 Task Variation Generation:")
    task_variations = experiment_config.generate_task_variations()
    print(f"   - Total variations: {len(task_variations)}")

    for i, variation in enumerate(task_variations):
        print(f"   - Variation {i+1}: {variation.name}")
        for step in variation.steps:
            if step.config:
                print(f"     Step '{step.name}': {step.config}")

    # Display evaluation configuration with target datasets
    print("\n📊 Evaluation Configuration:")
    print("   - Step-level evaluations:")
    for step_name in ["generate_greeting", "llm_response"]:
        step_evaluations = experiment_config.get_evaluation_config(step_name)
        target_datasets = experiment_config.get_target_datasets_for_step(step_name)
        if step_evaluations:
            print(f"     * {step_name}: {len(step_evaluations)} evaluators")
            print(f"       Target datasets: {target_datasets}")
            for eval_config in step_evaluations:
                print(f"         - {eval_config.name} ({eval_config.type})")
                if eval_config.parameters:
                    print(f"           Parameters: {eval_config.parameters}")

    print("   - Task-level evaluations:")
    task_evaluations = experiment_config.get_evaluation_config()
    task_target_datasets = experiment_config.get_target_datasets_for_task()
    if task_evaluations:
        print(f"     * Task: {len(task_evaluations)} evaluators")
        print(f"       Target datasets: {task_target_datasets}")
        for eval_config in task_evaluations:
            print(f"         - {eval_config.name} ({eval_config.type})")
            if eval_config.parameters:
                print(f"           Parameters: {eval_config.parameters}")

    # Run the experiments
    print(f"\n🚀 Running {len(task_variations)} task variations with evaluation...")
    print("=" * 70)

    try:
        # Run experiments synchronously
        results = run_yaml_experiments_sync(experiment_config)

        # Display results
        print("\n🎉 Task variations with evaluation completed successfully!")
        print("=" * 70)
        print(f"Configuration: {results['configuration_name']}")
        print(f"Total variations: {results['total_variations']}")
        print(f"Total runs: {results['summary']['total_runs']}")
        print(f"Successful: {results['summary']['successful']}")
        print(f"Failed: {results['summary']['failed']}")

        # Show detailed results for each variation
        print("\n📊 Detailed Results:")
        for var_key, var_results in results["variations"].items():
            print(f"\n--- {var_key} ---")
            print(f"   Name: {var_results['name']}")
            print(f"   Success: {'✅' if var_results['success'] else '❌'}")
            print(f"   Total runs: {var_results['total_runs']}")
            print(f"   Successful runs: {var_results['successful_runs']}")
            print(f"   Failed runs: {var_results['failed_runs']}")

            if var_results["errors"]:
                print(f"   Errors: {len(var_results['errors'])}")
                for error in var_results["errors"][:3]:  # Show first 3 errors
                    print(f"     - {error}")

            # Show step configurations for this variation
            if var_results["step_configs"]:
                print("   Step configurations:")
                for step_name, config in var_results["step_configs"].items():
                    print(f"     * {step_name}: {config}")

            # Show dataset results
            for dataset_name, dataset_result in var_results["dataset_results"].items():
                status = "✅" if dataset_result.get("success", False) else "❌"
                print(f"   Dataset {dataset_name}: {status}")
                if dataset_result.get("success", False):
                    print(
                        f"     Evaluators: {dataset_result.get('evaluator_count', 'N/A')}"
                    )
                    print(
                        f"     Results type: {dataset_result.get('results_type', 'N/A')}"
                    )
                    if dataset_result.get("has_detailed_results", False):
                        print(
                            f"     Evaluation count: {dataset_result.get('evaluation_count', 'N/A')}"
                        )
                    if dataset_result.get("step_name"):
                        print(f"     Step: {dataset_result.get('step_name')}")

        print("\n🔍 Check LangSmith for experiment results:")
        print("   1. Go to: https://smith.langchain.com/")
        print("   2. Navigate to your project: hex_machina_v2")
        print("   3. Look for experiments with prefixes:")
        for i in range(len(task_variations)):
            print(
                f"      - {experiment_config.settings.experiment_prefix}_variation_{i+1}_*"
            )

    except Exception as e:
        print(f"❌ Experiment execution failed: {e}")
        import traceback

        traceback.print_exc()

    print("\n🎉 Task variation system test completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
