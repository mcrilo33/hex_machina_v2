#!/usr/bin/env python3
"""
Test script to run the experiment configuration and show generated variations.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def load_experiment_config(config_path: str) -> Dict[str, Any]:
    """Load experiment configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def generate_task_variations(task_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate all possible task variations based on multi-value fields."""
    import itertools

    # Find all multi-value fields
    multi_value_fields = {}
    for step in task_config.get("steps", []):
        step_name = step.get("name", "unnamed")
        config = step.get("config", {})
        for field_name, field_value in config.items():
            if isinstance(field_value, list):
                # Store as step_name.field_name for easy lookup
                key = f"{step_name}.{field_name}"
                multi_value_fields[key] = field_value
                print(
                    f"      Found field: {key} = {field_value} (length: {len(field_value)})"
                )

    if not multi_value_fields:
        # No variations, return original task
        return [task_config]

    # Generate all combinations
    field_keys = list(multi_value_fields.keys())
    field_values = list(multi_value_fields.values())

    print(f"      Generating combinations for {len(field_keys)} fields...")

    variations = []
    for i, combination in enumerate(itertools.product(*field_values)):
        # Create a copy of the task
        variation = task_config.copy()
        variation["name"] = f"{task_config.get('name', 'task')}_variation_{i + 1}"

        # Apply the combination to the appropriate step and field
        for j, (field_key, value) in enumerate(zip(field_keys, combination)):
            step_name, config_field = field_key.split(".", 1)

            # Find the step and update its config
            for step in variation["steps"]:
                if step["name"] == step_name:
                    if "config" not in step:
                        step["config"] = {}
                    step["config"][config_field] = value
                    break

        variations.append(variation)

    return variations


def test_experiment_execution():
    """Test the experiment configuration execution."""

    print("🧪 Testing Experiment Configuration Execution")
    print("=" * 60)

    # 1. Load configuration
    print("\n1️⃣ Loading experiment configuration...")
    try:
        config = load_experiment_config("test_experiment_evaluation.yaml")
        print("✅ Configuration loaded successfully")
        print(f"   Name: {config.get('name', 'unnamed')}")
        print(f"   Description: {config.get('description', 'no description')}")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False

    # 2. Generate task variations
    print("\n2️⃣ Generating task variations...")
    task_config = config.get("task", {})
    variations = generate_task_variations(task_config)
    print(f"✅ Generated {len(variations)} task variations")

    # 3. Show variations
    print("\n3️⃣ Task Variations:")
    for i, variation in enumerate(variations):
        print(f"\n   📋 Variation {i + 1}: {variation['name']}")
        for step in variation.get("steps", []):
            step_name = step.get("name", "unnamed")
            runnable = step.get("runnable", "no runnable")
            step_config = step.get("config", {})

            print(f"      Step: {step_name} ({runnable})")
            for key, value in step_config.items():
                if isinstance(value, list):
                    print(f"        {key}: {value}")
                else:
                    print(f"        {key}: {value}")

    # 4. Show evaluation configuration
    print("\n4️⃣ Evaluation Configuration:")
    evaluations = config.get("evaluations", {})

    if "steps" in evaluations:
        print(f"   ✅ Found {len(evaluations['steps'])} step evaluations")
        for step_name, step_eval in evaluations["steps"].items():
            target_datasets = step_eval.get("target_datasets", [])
            evaluators = step_eval.get("evaluators", [])
            print(f"\n   📊 {step_name}:")
            print(f"      Target datasets: {target_datasets}")
            print(f"      Evaluators: {len(evaluators)}")
            for evaluator in evaluators:
                eval_name = evaluator.get("name", "unnamed")
                eval_type = evaluator.get("type", "no type")
                print(f"        - {eval_name} ({eval_type})")
    else:
        print("   ❌ No step evaluations found")

    # 5. Show settings
    print("\n5️⃣ Experiment Settings:")
    settings = config.get("settings", {})
    print(f"   Experiment prefix: {settings.get('experiment_prefix', 'default')}")
    print(f"   Save results: {settings.get('save_results', False)}")
    print(f"   Metadata: {settings.get('metadata', {})}")

    # 6. Summary
    print("\n" + "=" * 60)
    print("🎉 Experiment Configuration Test Summary:")
    print(f"   📋 Total task variations: {len(variations)}")
    print(f"   📊 Evaluation steps: {len(evaluations.get('steps', {}))}")

    # Count multi-value fields correctly
    multi_value_count = 0
    for step in variations[0].get("steps", []):
        step_config = step.get("config", {})
        for value in step_config.values():
            if isinstance(value, list):
                multi_value_count += 1

    print(f"   🔧 Multi-value fields: {multi_value_count}")

    # Show what combinations were generated
    print("\n   🔍 Variation breakdown:")
    for step in variations[0].get("steps", []):
        step_name = step.get("name", "unnamed")
        step_config = step.get("config", {})
        for key, value in step_config.items():
            if isinstance(value, list):
                print(f"      {step_name}.{key}: {len(value)} values → {value}")

    return True


if __name__ == "__main__":
    success = test_experiment_execution()
    if not success:
        print("\n❌ Experiment configuration test failed!")
        sys.exit(1)
    else:
        print("\n✅ Experiment configuration is ready for execution!")
