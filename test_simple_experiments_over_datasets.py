#!/usr/bin/env python3
"""
Simple experiment script that runs experiments OVER existing datasets using LangSmith's aevaluate.

This follows LangSmith's philosophy of simple, direct evaluation over datasets.
"""

import asyncio

from dotenv import load_dotenv
from langchain_core.runnables import RunnableLambda
from langsmith import Client, aevaluate


def helpfulness_evaluator(run, example):
    """Simple helpfulness evaluator that follows LangSmith's pattern."""
    # This is a basic evaluator that follows LangSmith's evaluation pattern
    # It takes a run and example and returns evaluation results

    # For now, return a simple score based on output length
    # In practice, this could use an LLM to evaluate the content
    output = run.outputs.get("result", "")
    if isinstance(output, str):
        # Simple heuristic: longer responses might be more helpful
        score = min(1.0, len(output) / 100.0)
    else:
        score = 0.5

    return {
        "score": score,
        "reasoning": f"Output length: {len(str(output))} characters",
        "criterion": "helpfulness",
    }


def conciseness_evaluator(run, example):
    """Simple conciseness evaluator."""
    output = run.outputs.get("result", "")
    if isinstance(output, str):
        # Shorter responses get higher conciseness scores
        score = max(0.0, 1.0 - (len(output) / 200.0))
    else:
        score = 0.5

    return {
        "score": score,
        "reasoning": f"Output length: {len(str(output))} characters",
        "criterion": "conciseness",
    }


async def run_simple_experiments_over_datasets():
    """Run simple experiments over existing datasets."""
    print("🚀 Running Simple Experiments OVER Existing Datasets")
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
            "name": "helpfulness_experiment",
            "description": "Test helpfulness of responses in existing datasets",
            "evaluators": [helpfulness_evaluator],
        },
        {
            "name": "conciseness_experiment",
            "description": "Test conciseness of responses in existing datasets",
            "evaluators": [conciseness_evaluator],
        },
        {
            "name": "combined_evaluation_experiment",
            "description": "Test both helpfulness and conciseness",
            "evaluators": [helpfulness_evaluator, conciseness_evaluator],
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
                # Run evaluation using LangSmith's aevaluate
                print(
                    f"   Running evaluation with {len(experiment_config['evaluators'])} evaluators..."
                )

                results = await aevaluate(
                    RunnableLambda(
                        lambda x: x
                    ),  # Wrap in RunnableLambda for LangSmith compatibility
                    dataset_name,  # Positional data argument
                    evaluators=experiment_config["evaluators"],
                    experiment_prefix=f"{experiment_config['name']}_{dataset_name}",
                    description=f"Experiment: {experiment_config['description']} on {dataset_name}",
                    metadata={
                        "experiment_name": experiment_config["name"],
                        "dataset_name": dataset_name,
                        "evaluation_type": "simple_experiment_over_dataset",
                        "evaluator_count": len(experiment_config["evaluators"]),
                    },
                )

                print("   ✅ Evaluation completed successfully!")
                print(f"   Results type: {type(results)}")

                # Show some result details
                if hasattr(results, "results") and results.results:
                    print(f"   Number of evaluations: {len(results.results)}")
                    # Show first few results
                    for j, result in enumerate(results.results[:3]):
                        print(f"     Result {j+1}: {result}")
                else:
                    print("   No results attribute or empty results")

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
    print("\n🔍 The experiments should now appear in LangSmith!")


def main():
    """Run the async experiments."""
    print("🚀 Starting Simple Experiments Over Existing Datasets")
    print("=" * 70)

    try:
        # Run the async experiments
        asyncio.run(run_simple_experiments_over_datasets())
    except Exception as e:
        print(f"❌ Main execution failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
