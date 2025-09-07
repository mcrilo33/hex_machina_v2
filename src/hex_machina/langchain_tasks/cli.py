"""
CLI for LangChain tasks and experiments.

This module provides a simple command-line interface to run tasks and experiments
from YAML configuration files, following LangChain's philosophy of simplicity
and explicit configuration.
"""

import argparse
import logging
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
from .cache_utils import clear_cache, get_cache_info, setup_default_cache
from .config_utils import resolve_env_vars
from .datasets import StepDatasetManager


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
            return resolve_env_vars(config)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse YAML file {config_path}: {e}")


def run_task(
    config_path: Path, article_id: Optional[int] = None, enable_caching: bool = True
) -> None:
    """Run a single task from YAML configuration.

    Args:
        config_path: Path to the YAML configuration file
        article_id: Optional article ID to process (for article-specific tasks)
        enable_caching: Whether to enable caching (default: True)
    """
    try:
        # Load configuration
        config = load_yaml_config(config_path)

        # Create dataset manager for handling datasets defined in config
        dataset_manager = StepDatasetManager()

        # Create task builder with caching preference and dataset manager
        builder = TaskBuilder(
            enable_caching=enable_caching, dataset_manager=dataset_manager
        )

        # Build the task
        task = builder.invoke(config)
        print(f"Task '{config.get('name', 'Unknown')}' built successfully!")

        # Prepare inputs for execution
        inputs = {}
        if article_id:
            inputs["article_id"] = article_id
            print(f"Processing article ID: {article_id}")

        # Execute the task with tracing
        print("Executing task...")
        result = builder.invoke_with_tracing(config, inputs)

        print("Task executed successfully!")
        print(f"Result type: {type(result).__name__}")

        # Show a preview of the result
        if hasattr(result, "__len__") and len(result) > 0:
            print(f"Result contains {len(result)} items")
            if isinstance(result, list) and len(result) > 0:
                print(f"First item type: {type(result[0]).__name__}")
        else:
            print(f"Result: {result}")

    except Exception as e:
        print(f"Error running task: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def manage_cache(action: str) -> None:
    """Manage the SQLite cache.

    Args:
        action: Action to perform ('info', 'clear', 'setup')
    """
    try:
        if action == "info":
            cache_info = get_cache_info()
            print("Cache Information:")
            for key, value in cache_info.items():
                print(f"  {key}: {value}")

        elif action == "clear":
            clear_cache()
            print("Cache cleared successfully!")

        elif action == "setup":
            setup_default_cache()
            print("Cache setup completed!")

        else:
            print(f"Unknown cache action: {action}")
            print("Available actions: info, clear, setup")

    except Exception as e:
        print(f"Error managing cache: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LangChain Tasks CLI - Run tasks and experiments from YAML configuration"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Task command
    task_parser = subparsers.add_parser(
        "run", help="Run a task from YAML configuration"
    )
    task_parser.add_argument(
        "-c", "--config", required=True, help="Path to YAML configuration file"
    )
    task_parser.add_argument(
        "--article-id",
        type=int,
        help="Article ID to process (for article-specific tasks)",
    )
    task_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable SQLite caching for this task execution",
    )

    # Cache management commands
    cache_parser = subparsers.add_parser("cache", help="Manage SQLite cache")
    cache_parser.add_argument(
        "action", choices=["info", "clear", "setup"], help="Cache action to perform"
    )

    # Dataset management commands
    dataset_parser = subparsers.add_parser("dataset", help="Manage LangSmith datasets")
    dataset_subparsers = dataset_parser.add_subparsers(
        dest="dataset_command", help="Available dataset commands"
    )

    # Create-split command
    create_split_parser = dataset_subparsers.add_parser(
        "create-split", help="Create a split with positive examples from evaluator"
    )
    create_split_parser.add_argument(
        "dataset_name", help="Name of the LangSmith dataset to evaluate"
    )
    create_split_parser.add_argument(
        "evaluator_name", help="Name of the evaluator to use"
    )
    create_split_parser.add_argument(
        "--split-name",
        default="positiplite",
        help="Name for the new split (default: positive)",
    )

    # Delete-split command
    delete_split_parser = dataset_subparsers.add_parser(
        "delete-split", help="Delete a split from a dataset"
    )
    delete_split_parser.add_argument(
        "dataset_name", help="Name of the LangSmith dataset"
    )
    delete_split_parser.add_argument("split_name", help="Name of the split to delete")

    # Annotate command
    annotate_parser = dataset_subparsers.add_parser(
        "annotate", help="Run interactive annotation session on dataset"
    )
    annotate_parser.add_argument(
        "-c", "--config", required=True, help="Path to annotation configuration file"
    )

    # Parse arguments
    args = parser.parse_args()

    # Setup logging
    setup_logging()

    if args.command == "run":
        config_path = Path(args.config)
        validate_yaml_config(config_path)
        # Enable caching by default, unless --no-cache is specified
        enable_caching = not args.no_cache
        run_task(config_path, args.article_id, enable_caching)
    elif args.command == "cache":
        manage_cache(args.action)
    elif args.command == "dataset":
        if args.dataset_command == "create-split":
            from .datasets import create_split_with_evaluator

            create_split_with_evaluator(
                args.dataset_name, args.evaluator_name, args.split_name
            )
        elif args.dataset_command == "delete-split":
            from .datasets import delete_split

            delete_split(args.dataset_name, args.split_name)
        elif args.dataset_command == "annotate":
            from .datasets import run_interactive_annotation

            run_interactive_annotation(Path(args.config))
        else:
            dataset_parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
