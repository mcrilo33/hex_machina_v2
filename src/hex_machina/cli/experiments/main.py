"""
Experiments CLI for running and managing configuration optimization experiments.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import click

from src.hex_machina.enrichment.experiments.comparator import ExperimentComparator
from src.hex_machina.enrichment.experiments.config import ExperimentConfigLoader
from src.hex_machina.enrichment.experiments.runner import ExperimentRunner

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
def experiments():
    """Experiment management commands for configuration optimization."""
    pass


@experiments.command()
@click.argument("config_file")
@click.option(
    "--validate-only", is_flag=True, help="Only validate configuration without running"
)
def run(config_file: str, validate_only: bool):
    """Run an experiment from a configuration file."""
    try:
        # Load experiment configuration
        config_loader = ExperimentConfigLoader()

        # Extract experiment name from config file path
        config_path = Path(config_file)
        if config_path.suffix == ".yaml":
            experiment_name = config_path.stem
        else:
            experiment_name = config_path.name

        # Load configuration
        config = config_loader.load_experiment(experiment_name)

        # Validate configuration
        errors = config_loader.validate_experiment(config)
        if errors:
            click.echo("❌ Configuration validation failed:")
            for error in errors:
                click.echo(f"  - {error}")
            return

        click.echo("✅ Configuration validated successfully")

        if validate_only:
            click.echo("🔍 Configuration details:")
            click.echo(f"  Experiment: {config.experiment_name}")
            click.echo(f"  Description: {config.description}")
            click.echo(f"  Dataset: {config.evaluation_dataset}")
            click.echo(f"  Evaluators: {', '.join(config.evaluators)}")
            click.echo(f"  Configurations: {len(config.task_configs)}")
            for tc in config.task_configs:
                click.echo(f"    - {tc.name}: {tc.description}")
            return

        # Run experiment
        click.echo(f"🚀 Starting experiment: {config.experiment_name}")
        click.echo(f"📊 Testing {len(config.task_configs)} configurations...")

        runner = ExperimentRunner()

        # Run experiment asynchronously
        async def run_experiment():
            return await runner.run_experiment(config)

        results = asyncio.run(run_experiment())

        # Display results
        click.echo("\n" + "=" * 60)
        click.echo("📊 EXPERIMENT RESULTS")
        click.echo("=" * 60)

        summary = results.get("summary", {})
        click.echo(f"✅ Successful runs: {summary.get('successful_runs', 0)}")
        click.echo(f"❌ Failed runs: {summary.get('failed_runs', 0)}")

        if summary.get("best_configuration"):
            click.echo(f"🏆 Best configuration: {summary['best_configuration']}")
            click.echo(f"📈 Best score: {summary.get('best_score', 0):.3f}")

        click.echo("\n📋 Configuration Scores:")
        for config_name, score in summary.get("scores", {}).items():
            click.echo(f"  {config_name}: {score:.3f}")

        click.echo("=" * 60)

    except Exception as e:
        click.echo(f"❌ Experiment failed: {e}")
        logger.exception("Experiment error")


@experiments.command()
def list():
    """List all available experiment configurations."""
    try:
        config_loader = ExperimentConfigLoader()
        experiments = config_loader.list_experiments()

        if not experiments:
            click.echo("📭 No experiment configurations found")
            click.echo("💡 Create experiment configs in config/experiments/")
            return

        click.echo(f"📋 Found {len(experiments)} experiment configuration(s):")
        click.echo()

        for i, experiment_name in enumerate(experiments, 1):
            try:
                config = config_loader.load_experiment(experiment_name)
                click.echo(f"{i:2d}. {experiment_name}")
                click.echo(f"    Description: {config.description}")
                click.echo(f"    Dataset: {config.evaluation_dataset}")
                click.echo(f"    Configurations: {len(config.task_configs)}")
                click.echo(f"    Evaluators: {len(config.evaluators)}")
                click.echo()
            except Exception as e:
                click.echo(f"{i:2d}. {experiment_name} (Error loading: {e})")
                click.echo()

    except Exception as e:
        click.echo(f"❌ Failed to list experiments: {e}")
        logger.exception("Error listing experiments")


@experiments.command()
@click.argument("experiment_name")
def show(experiment_name: str):
    """Show details of an experiment configuration."""
    try:
        config_loader = ExperimentConfigLoader()
        config = config_loader.load_experiment(experiment_name)

        click.echo(f"📋 Experiment: {config.experiment_name}")
        click.echo(f"📝 Description: {config.description}")
        click.echo(f"📅 Created: {config.created_at}")
        click.echo()

        click.echo("🔍 Evaluation Settings:")
        click.echo(f"  Dataset: {config.evaluation_dataset}")
        if config.evaluation_split:
            click.echo(f"  Split: {config.evaluation_split}")
        click.echo(f"  Evaluators: {', '.join(config.evaluators)}")
        click.echo()

        click.echo("📊 Comparison Metrics:")
        click.echo(f"  Primary: {config.comparison_metrics.primary}")
        click.echo(f"  Secondary: {', '.join(config.comparison_metrics.secondary)}")
        click.echo(f"  Threshold: {config.comparison_metrics.threshold}")
        click.echo()

        click.echo("⚙️ Task Configurations:")
        for i, task_config in enumerate(config.task_configs, 1):
            click.echo(f"  {i}. {task_config.name}")
            click.echo(f"     Description: {task_config.description}")
            click.echo(f"     Model: {task_config.config.get('model', 'N/A')}")
            click.echo(
                f"     Temperature: {task_config.config.get('temperature', 'N/A')}"
            )
            click.echo(
                f"     Max Tokens: {task_config.config.get('max_tokens', 'N/A')}"
            )
            click.echo()

        click.echo("⚙️ Experiment Settings:")
        click.echo(f"  Max Concurrent Runs: {config.settings.max_concurrent_runs}")
        click.echo(f"  Timeout per Run: {config.settings.timeout_per_run}s")
        click.echo(
            f"  Save Intermediate Results: {config.settings.save_intermediate_results}"
        )

    except Exception as e:
        click.echo(f"❌ Failed to show experiment: {e}")
        logger.exception("Error showing experiment")


@experiments.command()
@click.argument("experiment_name")
def compare(experiment_name: str):
    """Compare results from multiple runs of an experiment."""
    try:
        comparator = ExperimentComparator()
        comparison = comparator.compare_experiment_results(experiment_name)

        if "error" in comparison:
            click.echo(f"❌ {comparison['error']}")
            return

        click.echo(f"📊 Comparison for experiment: {experiment_name}")
        click.echo(f"📈 Total runs: {comparison['total_runs']}")
        click.echo()

        summary = comparison.get("summary", {})
        if summary:
            click.echo("🏆 Overall Summary:")
            click.echo(
                f"  Best overall score: {summary.get('best_overall_score', 0):.3f}"
            )
            click.echo(
                f"  Best overall config: {summary.get('best_overall_config', 'N/A')}"
            )
            click.echo(
                f"  Most consistent config: {summary.get('most_consistent_config', 'N/A')}"
            )
            click.echo(f"  Average duration: {summary.get('average_duration', 0):.1f}s")
            click.echo()

            click.echo("📊 Configuration Performance:")
            for config_name, perf in summary.get("config_performance", {}).items():
                click.echo(f"  {config_name}:")
                click.echo(f"    Average: {perf['average_score']:.3f}")
                click.echo(
                    f"    Range: {perf['min_score']:.3f} - {perf['max_score']:.3f}"
                )
                click.echo(f"    Std Dev: {perf['std_dev']:.3f}")
                click.echo(f"    Runs: {perf['runs_count']}")
                click.echo()

        # Show recent runs
        click.echo("📋 Recent Runs:")
        for i, run in enumerate(comparison.get("runs", [])[:5], 1):
            click.echo(f"  {i}. {run.get('completed_at', 'N/A')}")
            click.echo(f"     Best score: {run.get('best_score', 0):.3f}")
            click.echo(f"     Duration: {run.get('duration', 0):.1f}s")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Failed to compare experiment: {e}")
        logger.exception("Error comparing experiment")


@experiments.command()
@click.argument("experiment_name")
@click.option("--output-dir", help="Output directory for report")
def report(experiment_name: str, output_dir: Optional[str]):
    """Generate a detailed comparison report for an experiment."""
    try:
        comparator = ExperimentComparator()
        report_file = comparator.generate_comparison_report(experiment_name, output_dir)

        click.echo(f"✅ Generated comparison report: {report_file}")

    except Exception as e:
        click.echo(f"❌ Failed to generate report: {e}")
        logger.exception("Error generating report")


@experiments.command()
@click.option("--experiment-name", help="Filter by experiment name")
def results(experiment_name: Optional[str]):
    """List experiment results."""
    try:
        runner = ExperimentRunner()
        results = runner.list_experiment_results(experiment_name)

        if not results:
            click.echo("📭 No experiment results found")
            return

        click.echo(f"📋 Found {len(results)} experiment result(s):")
        click.echo()

        for i, result in enumerate(results, 1):
            click.echo(f"{i:2d}. {result.get('experiment_name', 'Unknown')}")
            click.echo(f"    Started: {result.get('started_at', 'N/A')}")
            click.echo(f"    Completed: {result.get('completed_at', 'N/A')}")

            summary = result.get("summary", {})
            if summary:
                click.echo(
                    f"    Best config: {summary.get('best_configuration', 'N/A')}"
                )
                click.echo(f"    Best score: {summary.get('best_score', 0):.3f}")
                click.echo(
                    f"    Success rate: {summary.get('successful_runs', 0)}/{summary.get('total_configurations', 0)}"
                )

            click.echo(f"    File: {result.get('file', 'N/A')}")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Failed to list results: {e}")
        logger.exception("Error listing results")


if __name__ == "__main__":
    experiments()
