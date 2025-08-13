#!/usr/bin/env python3
"""
Test script to validate experiment YAML configuration and show generated variations.
"""

import sys
from pathlib import Path

import yaml

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_experiment_config():
    """Test the experiment configuration file."""

    config_path = Path("test_experiment_evaluation.yaml")

    print("🧪 Testing Experiment Configuration")
    print("=" * 50)

    # 1. Test YAML parsing
    print("\n1️⃣ Testing YAML parsing...")
    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
        print("✅ YAML parsed successfully")
    except Exception as e:
        print(f"❌ YAML parsing failed: {e}")
        return False

    # 2. Test basic structure
    print("\n2️⃣ Testing basic structure...")
    required_keys = ["name", "description", "task", "evaluations", "settings"]
    for key in required_keys:
        if key in config_data:
            print(f"✅ Found '{key}' key")
        else:
            print(f"❌ Missing '{key}' key")
            return False

    # 3. Test task structure
    print("\n3️⃣ Testing task structure...")
    task = config_data.get("task", {})
    if "steps" in task:
        print(f"✅ Found {len(task['steps'])} steps in task")
        for i, step in enumerate(task["steps"]):
            print(
                f"   Step {i+1}: {step.get('name', 'unnamed')} ({step.get('runnable', 'no runnable')})"
            )
    else:
        print("❌ No steps found in task")
        return False

    # 4. Test multi-value fields for variations
    print("\n4️⃣ Testing multi-value fields for variations...")
    multi_value_fields = {}
    for step in task["steps"]:
        step_name = step.get("name", "unnamed")
        config = step.get("config", {})
        for field_name, field_value in config.items():
            if isinstance(field_value, list) and len(field_value) > 1:
                if step_name not in multi_value_fields:
                    multi_value_fields[step_name] = {}
                multi_value_fields[step_name][field_name] = field_value
                print(
                    f"✅ Found multi-value field: {step_name}.{field_name} = {field_value}"
                )

    if not multi_value_fields:
        print("⚠️  No multi-value fields found - only 1 variation will be generated")
    else:
        print(f"✅ Found {len(multi_value_fields)} multi-value fields")

    # 5. Calculate total variations
    print("\n5️⃣ Calculating total variations...")
    total_variations = 1
    for step_name, fields in multi_value_fields.items():
        for field_name, values in fields.items():
            total_variations *= len(values)
            print(f"   {step_name}.{field_name}: {len(values)} values")

    print(f"✅ Total variations that will be generated: {total_variations}")

    # 6. Test evaluation configuration
    print("\n6️⃣ Testing evaluation configuration...")
    evaluations = config_data.get("evaluations", {})
    if "steps" in evaluations:
        print(f"✅ Found {len(evaluations['steps'])} step evaluations")
        for step_name, step_eval in evaluations["steps"].items():
            target_datasets = step_eval.get("target_datasets", [])
            evaluators = step_eval.get("evaluators", [])
            print(
                f"   {step_name}: {len(target_datasets)} target datasets, {len(evaluators)} evaluators"
            )
    else:
        print("❌ No step evaluations found")

    # 7. Test settings
    print("\n7️⃣ Testing settings...")
    settings = config_data.get("settings", {})
    if "experiment_prefix" in settings:
        print(f"✅ Experiment prefix: {settings['experiment_prefix']}")
    if "save_results" in settings:
        print(f"✅ Save results: {settings['save_results']}")

    print("\n" + "=" * 50)
    print("🎉 Configuration test completed successfully!")
    print(f"📊 This configuration will generate {total_variations} task variations")

    return True


if __name__ == "__main__":
    success = test_experiment_config()
    if not success:
        print("\n❌ Configuration test failed!")
        sys.exit(1)
    else:
        print("\n✅ Configuration is valid and ready to use!")
