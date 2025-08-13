#!/usr/bin/env python3
"""
Test script to run experiments OVER existing datasets using LangSmith's aevaluate.

This script will:
1. Use the existing datasets we generated earlier
2. Run experiments with different parameters OVER these datasets
3. Use LangSmith's aevaluate() to evaluate the datasets
4. Save the experiment results in LangSmith
"""

import asyncio

from dotenv import load_dotenv
from langsmith import Client, aevaluate

from src.hex_machina.langchain_tasks.evaluation import evaluator_registry


async def run_experiments_over_datasets():
    """Run experiments over existing datasets using LangSmith's aevaluate."""
    print("🚀 Running Experiments OVER Existing Datasets")
    print("=" * 70)

    # Load environment variables
    load_dotenv()
    print("✅ Environment variables loaded")

    # Initialize LangSmith client
    try:
        client = Client()
        print("✅ LangSmith client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize LangSmith client: {e}")
        return

    # Define the existing datasets we want to experiment on
    # These are the datasets we generated from our simple task
    existing_datasets = [
        "simple_greeting_task_generate_greeting_20250813_090059",
        "simple_greeting_task_llm_response_20250813_090115",
        "simple_greeting_task_task_20250813_090055",
    ]

    print("\n📊 Target datasets for experiments:")
    for dataset_name in existing_datasets:
        print(f"   - {dataset_name}")

    # Define experiment configurations
    experiments = [
        {
            "name": "temperature_experiment",
            "description": "Test different temperature settings on existing datasets",
            "evaluators": [
                {
                    "name": "criteria:helpfulness",
                    "hyperparameters": {"temperature": 0.1},
                },
                {
                    "name": "criteria:conciseness",
                    "hyperparameters": {"temperature": 0.1},
                },
            ],
        },
        {
            "name": "model_comparison_experiment",
            "description": "Compare different models on existing datasets",
            "evaluators": [
                {
                    "name": "criteria:helpfulness",
                    "hyperparameters": {"temperature": 0.1},
                }
            ],
        },
    ]

    print(f"\n🧪 Running {len(experiments)} experiments...")

    for i, experiment_config in enumerate(experiments):
        print(f"\n--- Experiment {i+1}: {experiment_config['name']} ---")
        print(f"Description: {experiment_config['description']}")

        # Run experiment on each dataset
        for dataset_name in existing_datasets:
            print(f"\n📝 Evaluating dataset: {dataset_name}")

            try:
                # Prepare evaluators
                evaluators = []
                for eval_config in experiment_config["evaluators"]:
                    evaluator_name = eval_config["name"]
                    evaluator_kwargs = eval_config.get("hyperparameters", {})

                    # Get the evaluator from registry
                    evaluator = evaluator_registry.get_evaluator(
                        evaluator_name, **evaluator_kwargs
                    )
                    evaluators.append(evaluator)

                # Run evaluation using LangSmith's aevaluate
                print(f"   Running evaluation with {len(evaluators)} evaluators...")

                results = await aevaluate(
                    target=lambda x: x,  # Identity function for dataset evaluation
                    data=dataset_name,
                    evaluators=evaluators,
                    experiment_prefix=f"{experiment_config['name']}_{dataset_name}",
                    description=f"Experiment: {experiment_config['description']} on {dataset_name}",
                    metadata={
                        "experiment_name": experiment_config["name"],
                        "dataset_name": dataset_name,
                        "evaluation_type": "experiment_over_dataset",
                    },
                )

                print("   ✅ Evaluation completed successfully!")
                print(f"   Results: {type(results)}")

                # You can access specific results here
                if hasattr(results, "results"):
                    print(
                        f"   Number of evaluations: {len(results.results) if results.results else 'N/A'}"
                    )

            except Exception as e:
                print(f"   ❌ Evaluation failed: {e}")
                import traceback

                traceback.print_exc()

    print("\n🎉 All experiments completed!")
    print("=" * 70)
    print("📋 Check LangSmith for experiment results:")
    print("   1. Go to: https://smith.langchain.com/")
    print("   2. Navigate to your project: hex-machina-v2")
    print("   3. Look for experiments with prefixes:")
    for exp in experiments:
        print(f"      - {exp['name']}_*")


def main():
    """Run the async experiments."""
    print("🚀 Starting Experiments Over Existing Datasets")
    print("=" * 70)

    try:
        # Run the async experiments
        asyncio.run(run_experiments_over_datasets())
    except Exception as e:
        print(f"❌ Main execution failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
