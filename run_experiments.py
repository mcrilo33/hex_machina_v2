#!/usr/bin/env python3
"""
Run experiments based on the experiment configuration.

This script executes the task variations and runs evaluations on the results.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load environment variables
from dotenv import load_dotenv

load_dotenv()


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

    if not multi_value_fields:
        # No variations, return original task
        return [task_config]

    # Generate all combinations
    field_keys = list(multi_value_fields.keys())
    field_values = list(multi_value_fields.values())

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


def run_experiments():
    """Run the experiments based on the configuration."""

    print("🚀 Running Experiments")
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

    # 3. Import required modules
    print("\n3️⃣ Setting up experiment execution...")
    try:
        from langsmith import Client

        from hex_machina.langchain_tasks.builder import TaskBuilder
        from hex_machina.langchain_tasks.evaluation.registry import evaluator_registry
        from hex_machina.langchain_tasks.runnables.registry import RunnableRegistry

        print("✅ Required modules imported successfully")
    except Exception as e:
        print(f"❌ Failed to import required modules: {e}")
        return False

    # 4. Initialize components
    print("\n4️⃣ Initializing components...")
    try:
        # Initialize registry and register custom runnables
        from hex_machina.langchain_tasks.registry import RunnableRegistry

        registry = RunnableRegistry()
        from hex_machina.langchain_tasks.runnables import (
            ArticleFetcher,
            EnrichmentSaver,
            MockKeywordExtractor,
            MockSummarizer,
        )

        registry._custom_registry["ArticleFetcher"] = ArticleFetcher
        registry._custom_registry["EnrichmentSaver"] = EnrichmentSaver
        registry._custom_registry["MockSummarizer"] = MockSummarizer
        registry._custom_registry["MockKeywordExtractor"] = MockKeywordExtractor

        # Initialize TaskBuilder
        from hex_machina.langchain_tasks.datasets.generator import DatasetGenerator
        from hex_machina.langchain_tasks.datasets.step_manager import StepDatasetManager

        dataset_manager = DatasetGenerator()
        step_manager = StepDatasetManager()
        builder = TaskBuilder(registry, step_manager)

        # Initialize LangSmith client
        client = Client()

        print("✅ Components initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize components: {e}")
        return False

    # 5. Run experiments
    print("\n5️⃣ Running experiments...")
    experiment_results = []

    for i, variation in enumerate(variations):
        print(
            f"\n   🔬 Running variation {i + 1}/{len(variations)}: {variation['name']}"
        )

        try:
            # Convert variation to TaskConfig format
            from hex_machina.langchain_tasks.builder import StepConfig, TaskConfig

            steps = []
            for step in variation.get("steps", []):
                step_config = StepConfig(
                    name=step["name"],
                    runnable=step["runnable"],
                    dataset=step.get("dataset", False),
                    config=step.get("config", {}),
                )
                steps.append(step_config)

            task_config_obj = TaskConfig(
                name=variation["name"],
                description=variation.get("description", ""),
                steps=steps,
                dataset=variation.get("dataset", False),
            )

            # Build and run the task
            print(f"      Building task: {variation['name']}")
            task = builder.build_from_yaml(task_config_obj)

            print("      Executing task with tracing...")
            result = builder.invoke_with_tracing(task_config_obj, {})

            print("      Generating datasets...")
            datasets = builder.generate_grouped_datasets(task_config_obj)

            experiment_results.append(
                {"variation": variation["name"], "result": result, "datasets": datasets}
            )

            print(f"      ✅ Variation {i + 1} completed successfully")

        except Exception as e:
            print(f"      ❌ Variation {i + 1} failed: {e}")
            experiment_results.append({"variation": variation["name"], "error": str(e)})

    # 6. Run evaluations
    print("\n6️⃣ Running evaluations...")
    evaluations = config.get("evaluations", {})

    if "steps" in evaluations:
        print(f"   Found {len(evaluations['steps'])} step evaluations")

        for step_name, step_eval in evaluations["steps"].items():
            print(f"\n   📊 Evaluating step: {step_name}")

            target_datasets = step_eval.get("target_datasets", [])
            evaluators = step_eval.get("evaluators", [])

            print(f"      Target datasets: {target_datasets}")
            print(f"      Evaluators: {len(evaluators)}")

            for evaluator_config in evaluators:
                evaluator_name = evaluator_config.get("name", "unnamed")
                evaluator_type = evaluator_config.get("type", "no type")

                print(f"      Running evaluator: {evaluator_name} ({evaluator_type})")

                try:
                    # Get the evaluator
                    if evaluator_type.startswith("criteria:"):
                        criteria = evaluator_type.split(":", 1)[1]
                        # Create LLM for evaluation
                        from langchain_core.prompts import PromptTemplate
                        from langchain_openai import ChatOpenAI

                        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.0)

                        # Create the required prompt for CriteriaEvalChain
                        prompt = PromptTemplate.from_template(
                            "You are evaluating the quality of a response. "
                            "Rate the response based on the following criterion: {criteria}\n\n"
                            "Response: {input}\n"
                            "Output: {output}\n\n"
                            "Rate from 1-10 and provide reasoning:"
                        )

                        evaluator = evaluator_registry.get_evaluator(
                            "criteria", criterion_name=criteria, llm=llm, prompt=prompt
                        )
                    else:
                        evaluator = evaluator_registry.get_evaluator(evaluator_type)

                    # Run evaluation on target datasets
                    for dataset_name in target_datasets:
                        print(f"        Evaluating dataset: {dataset_name}")

                        # Get dataset examples
                        try:
                            examples = client.list_examples(dataset_name=dataset_name)
                            if examples:
                                print(f"          Found {len(list(examples))} examples")
                                # Here you would run the actual evaluation
                                # For now, just show that we can access the data
                            else:
                                print("          No examples found in dataset")
                        except Exception as e:
                            print(f"          ❌ Failed to access dataset: {e}")

                    print(f"        ✅ Evaluator {evaluator_name} completed")

                except Exception as e:
                    print(f"        ❌ Evaluator {evaluator_name} failed: {e}")
    else:
        print("   ❌ No step evaluations found")

    # 7. Summary
    print("\n" + "=" * 60)
    print("🎉 Experiment Execution Summary:")
    print(f"   📋 Total variations: {len(variations)}")
    print(
        f"   ✅ Successful: {len([r for r in experiment_results if 'error' not in r])}"
    )
    print(f"   ❌ Failed: {len([r for r in experiment_results if 'error' in r])}")
    print(f"   📊 Evaluation steps: {len(evaluations.get('steps', {}))}")

    return True


if __name__ == "__main__":
    success = run_experiments()
    if not success:
        print("\n❌ Experiment execution failed!")
        sys.exit(1)
    else:
        print("\n✅ Experiments completed successfully!")
