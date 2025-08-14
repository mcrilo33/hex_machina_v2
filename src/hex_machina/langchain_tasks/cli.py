"""
CLI for LangChain tasks and experiments.

This module provides a simple command-line interface to run tasks and experiments
from YAML configuration files, following LangChain's philosophy of simplicity
and explicit configuration.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import yaml

# Load environment variables from .env files
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass

from ..experiments import ExperimentYAMLRunner
from .builder import TaskBuilder
from .registry import RunnableRegistry


def setup_logging() -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def validate_yaml_config(config_path: Path) -> Path:
    """Validate that the YAML config file exists and is readable.

    Args:
        config_path: Path to the YAML config file

    Returns:
        Validated Path object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If file is not a YAML file
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    if config_path.suffix.lower() not in [".yaml", ".yml"]:
        raise ValueError(f"Configuration file must be YAML: {config_path}")

    return config_path


def load_yaml_config(config_path: Path) -> dict:
    """Load YAML configuration file.

    Args:
        config_path: Path to the YAML config file

    Returns:
        Dictionary containing the configuration

    Raises:
        yaml.YAMLError: If YAML parsing fails
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            # Resolve environment variables in config values
            return _resolve_env_vars(config)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse YAML file {config_path}: {e}")


def _resolve_env_vars(obj):
    """Recursively resolve environment variables in config values."""
    if isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_vars(item) for item in obj]
    elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        env_var = obj[2:-1]  # Remove ${ and }
        return os.getenv(env_var, obj)  # Return original if env var not found
    else:
        return obj


def run_task(config_path: Path, article_id: Optional[int] = None) -> None:
    """Run a single task from YAML configuration.

    Args:
        config_path: Path to the YAML configuration file
        article_id: Optional article ID to process
    """
    logger = logging.getLogger("langchain_tasks.cli")

    try:
        # Validate and load configuration
        config_path = validate_yaml_config(config_path)
        config_dict = load_yaml_config(config_path)

        logger.info(f"Running task from configuration: {config_path}")

        # Build and run task
        registry = RunnableRegistry()

        # Create dataset manager to enable dataset creation
        from .datasets.step_manager import StepDatasetManager

        dataset_manager = StepDatasetManager()

        builder = TaskBuilder(registry=registry, dataset_manager=dataset_manager)

        # Build the task
        task = builder.invoke(config_dict)
        logger.info(f"Task built successfully: {type(task).__name__}")

        # Prepare inputs
        inputs = {}
        if article_id:
            inputs["article_id"] = article_id
            logger.info(f"Processing article ID: {article_id}")

        logger.info("Executing task with tracing to enable dataset creation...")

        # Execute the task with tracing to enable dataset creation
        result = builder.invoke_with_tracing(config_dict, inputs)

        logger.info("Task completed successfully")
        logger.info(f"Result: {result}")

    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        raise


def run_experiment(config_path: Path, input_file: Optional[Path] = None) -> None:
    """Run an experiment from YAML configuration.

    Args:
        config_path: Path to the YAML configuration file
        input_file: Optional JSON file with test inputs
    """
    logger = logging.getLogger("langchain_tasks.cli")

    try:
        # Validate and load configuration
        config_path = validate_yaml_config(config_path)
        logger.info(f"Running experiment from configuration: {config_path}")

        # Load test inputs if provided
        if input_file:
            import json

            with open(input_file, "r") as f:
                inputs = json.load(f)
            logger.info(f"Loaded test inputs from: {input_file}")

        # Use our new ExperimentYAMLRunner
        experiment_runner = ExperimentYAMLRunner()

        # Execute experiment using the new runner
        logger.info("Executing experiment...")
        result = experiment_runner.run_experiment_from_yaml_sync(config_path)

        logger.info("Experiment completed successfully")
        logger.info(f"Target dataset: {result.get('target_dataset', 'unknown')}")
        logger.info(f"Task variations: {len(result.get('task_variations', []))}")
        logger.info(f"Evaluation results: {len(result.get('evaluation_results', []))}")

    except Exception as e:
        logger.error(f"Experiment execution failed: {e}")
        raise


def main() -> None:
    """Main CLI entry point."""
    setup_logging()
    logger = logging.getLogger("langchain_tasks.cli")

    parser = argparse.ArgumentParser(
        description="LangChain Tasks CLI - Run tasks and experiments from YAML configs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a single task
  langchain_tasks run -c configs/enrichment/tasks/content_completeness.yaml

  # Run a task with specific article ID
  langchain_tasks run -c configs/enrichment/tasks/content_completeness.yaml --article-id 123

  # Run an experiment
  langchain_tasks experiment -c configs/experiments/example_experiment.yaml

  # Run an experiment with test inputs
  langchain_tasks experiment -c configs/experiments/example_experiment.yaml --input-file test_inputs.json
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a single task from YAML config")
    run_parser.add_argument(
        "-c", "--config", type=Path, required=True, help="Path to task YAML config file"
    )
    run_parser.add_argument(
        "--article-id", type=int, help="Article ID from database (optional)"
    )

    # Experiment command
    experiment_parser = subparsers.add_parser(
        "experiment", help="Run experiments with multiple task variations"
    )
    experiment_parser.add_argument(
        "-c",
        "--config",
        type=Path,
        required=True,
        help="Path to experiment YAML config file",
    )
    experiment_parser.add_argument(
        "--input-file", type=Path, help="JSON file with test inputs (optional)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "run":
            run_task(args.config, args.article_id)
        elif args.command == "experiment":
            run_experiment(args.config, args.input_file)
        else:
            logger.error(f"Unknown command: {args.command}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"CLI execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
