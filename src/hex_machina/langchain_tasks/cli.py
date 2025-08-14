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

from .builder import TaskBuilder
from .experiments.yaml_runner import YAMLExperimentRunner
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
        config_path: Path to task YAML config
        article_id: Optional article ID from database
    """
    logger = logging.getLogger("langchain_tasks.cli.run")

    try:
        # Validate config file
        config_path = validate_yaml_config(config_path)
        logger.info(f"Running task from config: {config_path}")

        # Load YAML config
        config_dict = load_yaml_config(config_path)
        logger.info(f"Loaded configuration: {config_dict.get('name', 'unnamed')}")

        # Initialize components - Registry will auto-discover custom runnables
        registry = RunnableRegistry()

        # Initialize dataset manager for step-level datasets
        from .datasets.step_manager import StepDatasetManager

        dataset_manager = StepDatasetManager()

        task_builder = TaskBuilder(registry=registry, dataset_manager=dataset_manager)

        # Build and execute task
        task = task_builder.invoke(config_dict)

        # Prepare inputs (runnables will handle input sourcing)
        inputs = {}
        if article_id:
            inputs["article_id"] = article_id
            logger.info(f"Using article ID: {article_id}")

        # Execute task with tracing
        logger.info("Executing task...")
        result = task_builder.invoke_with_tracing(config_dict, inputs)

        logger.info("Task completed successfully")
        logger.info(f"Result: {result}")

    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        raise


def run_experiment(config_path: Path, input_file: Optional[Path] = None) -> None:
    """Run an experiment from YAML configuration.

    Args:
        config_path: Path to experiment YAML config
        input_file: Optional JSON file with test inputs
    """
    logger = logging.getLogger("langchain_tasks.cli.experiment")

    try:
        # Validate config file
        config_path = validate_yaml_config(config_path)
        logger.info(f"Running experiment from config: {config_path}")

        # Load YAML config
        config_dict = load_yaml_config(config_path)
        logger.info(
            f"Loaded experiment configuration: {config_dict.get('name', 'unnamed')}"
        )

        # Initialize components - Registry will auto-discover custom runnables
        registry = RunnableRegistry()
        task_builder = TaskBuilder(registry=registry)

        # Always use YAMLExperimentRunner for experiments
        experiment_runner = YAMLExperimentRunner()

        # Load test inputs if provided
        inputs = {}
        if input_file:
            if not input_file.exists():
                raise FileNotFoundError(f"Input file not found: {input_file}")
            if not input_file.suffix.lower() == ".json":
                raise ValueError(f"Input file must be JSON: {input_file}")

            import json

            with open(input_file, "r") as f:
                inputs = json.load(f)
            logger.info(f"Loaded test inputs from: {input_file}")

        # Instantiate the proper configuration model
        from .config.models import ExperimentConfig

        experiment_config = ExperimentConfig(**config_dict)

        # Execute experiment
        logger.info("Executing experiment...")
        # YAMLExperimentRunner is async, use sync wrapper
        result = experiment_runner.run_sync(
            experiment_runner.run_experiments_from_config(experiment_config)
        )

        logger.info("Experiment completed successfully")
        logger.info(f"Total variations: {result.get('total_variations', 'unknown')}")
        logger.info(f"Datasets created: {len(result.get('datasets_created', []))}")

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
  langchain_tasks experiment -c configs/ingestion/experiments/content_completeness_optimization.yaml

  # Run an experiment with test inputs
  langchain_tasks experiment -c configs/ingestion/experiments/content_completeness_optimization.yaml --input-file test_inputs.json
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
