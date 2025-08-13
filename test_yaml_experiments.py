#!/usr/bin/env python3
"""
Test script for the YAML-based experiment system.

This script demonstrates how to:
1. Load experiment configuration from YAML
2. Parse it using Pydantic models
3. Run experiments using the YAML runner
4. Integrate with LangSmith for evaluation
"""

import yaml
from dotenv import load_dotenv

from src.hex_machina.langchain_tasks.experiments import (
    ExperimentConfiguration,
    run_yaml_experiments_sync,
)


def main():
    """Test the YAML-based experiment system."""
    print("🚀 Testing YAML-Based Experiment System")
    print("=" * 70)

    # Load environment variables
    load_dotenv()
    print("✅ Environment variables loaded")

    # Load the experiment configuration
    try:
        with open("test_experiment_config_with_evaluators.yaml", "r") as f:
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
        print(f"✅ Target datasets: {len(experiment_config.target_datasets)}")
        print(f"✅ Experiments: {len(experiment_config.experiments)}")
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

    print("\n📊 Target Datasets:")
    for dataset in experiment_config.target_datasets:
        print(f"   - {dataset}")

    print("\n🧪 Experiments:")
    for exp_key, experiment in experiment_config.experiments.items():
        print(f"   - {exp_key}: {experiment.name}")
        print(f"     Description: {experiment.description}")
        print(f"     Evaluators: {len(experiment.evaluators)}")
        for evaluator in experiment.evaluators:
            print(f"       * {evaluator.name} ({evaluator.type})")
            if evaluator.parameters:
                print(f"         Parameters: {evaluator.parameters}")

    # Run the experiments
    print(f"\n🚀 Running {len(experiment_config.experiments)} experiments...")
    print("=" * 70)

    try:
        # Run experiments synchronously
        results = run_yaml_experiments_sync(experiment_config)

        # Display results
        print("\n🎉 Experiments completed successfully!")
        print("=" * 70)
        print(f"Configuration: {results['configuration_name']}")
        print(f"Total experiments: {results['total_experiments']}")
        print(f"Total datasets: {results['total_datasets']}")
        print(f"Total runs: {results['summary']['total_runs']}")
        print(f"Successful: {results['summary']['successful']}")
        print(f"Failed: {results['summary']['failed']}")

        # Show detailed results for each experiment
        print("\n📊 Detailed Results:")
        for exp_key, exp_results in results["experiments"].items():
            print(f"\n--- {exp_key} ---")
            print(f"   Name: {exp_results['name']}")
            print(f"   Success: {'✅' if exp_results['success'] else '❌'}")
            print(f"   Total runs: {exp_results['total_runs']}")
            print(f"   Successful runs: {exp_results['successful_runs']}")
            print(f"   Failed runs: {exp_results['failed_runs']}")

            if exp_results["errors"]:
                print(f"   Errors: {len(exp_results['errors'])}")
                for error in exp_results["errors"][:3]:  # Show first 3 errors
                    print(f"     - {error}")

            # Show dataset results
            for dataset_name, dataset_result in exp_results["dataset_results"].items():
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

        print("\n🔍 Check LangSmith for experiment results:")
        print("   1. Go to: https://smith.langchain.com/")
        print("   2. Navigate to your project: hex_machina_v2")
        print("   3. Look for experiments with prefixes:")
        for exp_key in experiment_config.experiments.keys():
            print(f"      - {experiment_config.settings.experiment_prefix}_{exp_key}_*")

    except Exception as e:
        print(f"❌ Experiment execution failed: {e}")
        import traceback

        traceback.print_exc()

    print("\n🎉 YAML-based experiment system test completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
