#!/usr/bin/env python3
"""
Test script for the new evaluation and experiment system.

This script tests:
1. Configuration parsing with multiple values
2. Experiment variation generation
3. Evaluation system setup
"""

import yaml

from src.hex_machina.langchain_tasks.config.models import ExperimentConfig
from src.hex_machina.langchain_tasks.evaluation import (
    EvaluationRunner,
    evaluator_registry,
)
from src.hex_machina.langchain_tasks.experiments import ExperimentRunner


def test_config_parsing():
    """Test parsing of experiment configuration with multiple values."""
    print("🧪 Testing Configuration Parsing")
    print("=" * 50)

    # Load the experiment config
    with open("test_experiment_config.yaml", "r") as f:
        config_data = yaml.safe_load(f)

    # Parse into ExperimentConfig
    experiment_config = ExperimentConfig(**config_data)

    print(f"✅ Experiment: {experiment_config.name}")
    print(f"✅ Description: {experiment_config.description}")
    print(f"✅ Task: {experiment_config.task.name}")
    print(f"✅ Steps: {len(experiment_config.task.steps)}")

    # Check for multiple values
    for step in experiment_config.task.steps:
        if hasattr(step, "_multi_value_fields") and step._multi_value_fields:
            print(f"✅ Step '{step.name}' has multiple values:")
            for field, values in step._multi_value_fields.items():
                print(f"   - {field}: {values}")

    return experiment_config


def test_variation_generation(experiment_config: ExperimentConfig):
    """Test generation of task variations from multiple values."""
    print("\n🧪 Testing Variation Generation")
    print("=" * 50)

    # Generate variations
    variations = experiment_config.generate_task_variations()

    print(f"✅ Generated {len(variations)} task variations")

    for i, variation in enumerate(variations):
        print(f"\n📋 Variation {i}:")
        print(f"   - Task: {variation.name}")
        print(f"   - Steps: {len(variation.steps)}")

        for step in variation.steps:
            if step.config:
                print(f"   - Step '{step.name}' config: {step.config}")

    return variations


def test_evaluator_registry():
    """Test the evaluator registry."""
    print("\n🧪 Testing Evaluator Registry")
    print("=" * 50)

    # List available evaluators
    evaluators = evaluator_registry.list_evaluators()
    print(f"✅ Built-in evaluators: {evaluators['builtin']}")
    print(f"✅ Custom evaluators: {evaluators['custom']}")

    # Test getting specific evaluators
    try:
        # Test criteria evaluator
        criteria_eval = evaluator_registry.get_evaluator("criteria:helpfulness")
        print("✅ Successfully got criteria evaluator")

        # Test getting evaluator info
        info = evaluator_registry.get_evaluator_info("criteria:helpfulness")
        print(f"✅ Evaluator info: {info}")

    except Exception as e:
        print(f"❌ Failed to get evaluator: {e}")

    return evaluator_registry


def test_evaluation_runner():
    """Test the evaluation runner setup."""
    print("\n🧪 Testing Evaluation Runner")
    print("=" * 50)

    try:
        evaluation_runner = EvaluationRunner()
        print("✅ Evaluation runner created successfully")

        # Test finding datasets (should be empty for now)
        step_datasets = evaluation_runner._find_step_datasets(
            "test_experiment", "test_step"
        )
        print(f"✅ Step datasets found: {len(step_datasets)}")

        task_datasets = evaluation_runner._find_task_datasets("test_experiment")
        print(f"✅ Task datasets found: {len(task_datasets)}")

        return evaluation_runner

    except Exception as e:
        print(f"❌ Failed to create evaluation runner: {e}")
        return None


def test_experiment_runner():
    """Test the experiment runner setup."""
    print("\n🧪 Testing Experiment Runner")
    print("=" * 50)

    try:
        experiment_runner = ExperimentRunner()
        print("✅ Experiment runner created successfully")
        return experiment_runner

    except Exception as e:
        print(f"❌ Failed to create experiment runner: {e}")
        return None


def main():
    """Run all tests."""
    print("🚀 Testing Evaluation + Experiment System")
    print("=" * 60)

    # Test 1: Configuration parsing
    experiment_config = test_config_parsing()

    # Test 2: Variation generation
    variations = test_variation_generation(experiment_config)

    # Test 3: Evaluator registry
    registry = test_evaluator_registry()

    # Test 4: Evaluation runner
    eval_runner = test_evaluation_runner()

    # Test 5: Experiment runner
    exp_runner = test_experiment_runner()

    print("\n🎉 All Tests Completed!")
    print("=" * 60)

    if all([experiment_config, variations, registry, eval_runner, exp_runner]):
        print("✅ All components working correctly!")
        print("\n📋 Next steps:")
        print("   1. Run experiments to generate datasets")
        print("   2. Use evaluation runner to evaluate datasets")
        print("   3. Check results in LangSmith UI")
    else:
        print("❌ Some components failed - check the logs above")


if __name__ == "__main__":
    main()
