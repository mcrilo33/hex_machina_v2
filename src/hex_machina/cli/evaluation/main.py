"""
Evaluation CLI for running evaluators on workflow results or datasets.
"""

import logging
from typing import Any, Dict, Optional

import click
from dotenv import load_dotenv

from src.hex_machina.enrichment.evaluation.evaluation_functions import (
    evaluate_dataset_examples,
    evaluate_workflow_operation,
    list_available_evaluators,
)
from src.hex_machina.enrichment.evaluation.langsmith_integration import (
    setup_langsmith_environment,
)

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
def evaluation():
    """Evaluation commands for assessing task outputs and datasets."""
    pass


@evaluation.command()
@click.option("--workflow-operation-id", help="Workflow operation to evaluate")
@click.option("--dataset", help="Dataset to evaluate")
@click.option("--split", help="Dataset split to evaluate")
@click.option("--evaluators", required=True, help="Comma-separated evaluators")
@click.option("--experiment-name", help="Name for the experiment")
@click.option("--output-file", help="Save results to JSON file")
def evaluate(
    workflow_operation_id: Optional[str],
    dataset: Optional[str],
    split: Optional[str],
    evaluators: str,
    experiment_name: Optional[str],
    output_file: Optional[str],
):
    """Evaluate workflow results or dataset examples using specified evaluators."""

    try:
        # Parse evaluators
        evaluator_list = [e.strip() for e in evaluators.split(",")]

        # Setup LangSmith environment
        setup_langsmith_environment()

        # Smart detection and evaluation
        if workflow_operation_id:
            click.echo(f"🔍 Evaluating workflow operation: {workflow_operation_id}")
            results = evaluate_workflow_operation(
                workflow_operation_id=workflow_operation_id,
                evaluators=evaluator_list,
                experiment_name=experiment_name,
            )
        elif dataset:
            click.echo(
                f"🔍 Evaluating dataset: {dataset}"
                + (f" (split: {split})" if split else "")
            )
            results = evaluate_dataset_examples(
                dataset_name=dataset,
                split=split,
                evaluators=evaluator_list,
                experiment_name=experiment_name,
            )
        else:
            click.echo("❌ Must specify either --workflow-operation-id or --dataset")
            return

        # Display results
        display_evaluation_results(results, experiment_name)

        # Save results if requested
        if output_file:
            save_evaluation_results(results, output_file)
            click.echo(f"💾 Results saved to: {output_file}")

    except Exception as e:
        click.echo(f"❌ Evaluation failed: {e}")
        logger.exception("Evaluation error")


@evaluation.command()
def list_evaluators():
    """List all available evaluators."""
    try:
        evaluators = list_available_evaluators()

        click.echo("\n" + "=" * 60)
        click.echo("📋 AVAILABLE EVALUATORS")
        click.echo("=" * 60)

        for i, evaluator in enumerate(evaluators, 1):
            click.echo(f"{i:2d}. {evaluator['name']}")
            click.echo(f"    Provider: {evaluator['provider']}")
            click.echo(f"    Model: {evaluator['model']}")
            click.echo(f"    Description: {evaluator['description']}")
            click.echo()

        click.echo("=" * 60)
        click.echo("\n💡 Usage examples:")
        click.echo("  poetry run python -m src.hex_machina.cli evaluation evaluate \\")
        click.echo("    --workflow-operation-id 'batch_xxx' \\")
        click.echo("    --evaluators criteria_completeness,criteria_accuracy")
        click.echo()
        click.echo("  poetry run python -m src.hex_machina.cli evaluation evaluate \\")
        click.echo("    --dataset my-dataset \\")
        click.echo("    --evaluators qa,embedding_distance")

    except Exception as e:
        click.echo(f"❌ Failed to list evaluators: {e}")
        logger.exception("Error listing evaluators")


def display_evaluation_results(results: Dict[str, Any], experiment_name: Optional[str]):
    """Display evaluation results in a formatted way."""

    click.echo("\n" + "=" * 60)
    click.echo("📊 EVALUATION RESULTS")
    click.echo("=" * 60)

    for evaluator_name, result in results.items():
        if isinstance(result, dict) and "score" in result:
            score = result["score"]
            if isinstance(score, (int, float)):
                click.echo(f"✅ {evaluator_name}: {score:.2f}")
            else:
                click.echo(f"✅ {evaluator_name}: {score}")
        elif isinstance(result, dict) and "results" in result:
            # Handle batch results
            scores = [
                r.get("score", 0) for r in result["results"] if isinstance(r, dict)
            ]
            if scores:
                avg_score = sum(scores) / len(scores)
                click.echo(
                    f"✅ {evaluator_name}: {avg_score:.2f} avg ({len(scores)} items)"
                )
            else:
                click.echo(
                    f"✅ {evaluator_name}: {len(result['results'])} items evaluated"
                )
        else:
            click.echo(f"✅ {evaluator_name}: {result}")

    if experiment_name:
        click.echo(f"\n🔗 LangSmith Experiment: {experiment_name}")

    click.echo("=" * 60)


def save_evaluation_results(results: Dict[str, Any], output_file: str):
    """Save evaluation results to a JSON file."""
    import json
    from datetime import datetime

    output_data = {"timestamp": datetime.now().isoformat(), "results": results}

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2, default=str)


if __name__ == "__main__":
    evaluation()
