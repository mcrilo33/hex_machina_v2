"""
Command-line interface for running experiments.

Usage:
    poetry run python -m src.hex_machina.experiments -c <config_file>
    poetry run python -m src.hex_machina.experiments --cache-info
    poetry run python -m src.hex_machina.experiments --cache-clear
"""

import asyncio
import logging
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from ..langchain_tasks.cache_utils import clear_cache, get_cache_info
from ..langchain_tasks.config_utils import resolve_env_vars
from .config_models import ExperimentConfig
from .runner import ExperimentRunner


def load_environment():
    """Load environment variables from .env files."""
    # Try to load from current directory first
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment from: {env_path.absolute()}")
    else:
        # Try to load from project root
        project_root = Path(__file__).parent.parent.parent.parent
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded environment from: {env_path.absolute()}")
        else:
            print(
                "Warning: No .env file found. Environment variables may not be loaded."
            )
            print(
                "Please ensure your API keys are set in the environment or create a .env file."
            )


def load_experiment_config(config_path: str) -> ExperimentConfig:
    """Load experiment configuration from YAML file."""
    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Resolve environment variables in the config
        resolved_config_data = resolve_env_vars(config_data)

        return ExperimentConfig(**resolved_config_data)
    except Exception as e:
        print(f"Error loading experiment config: {e}")
        sys.exit(1)


def show_cache_info():
    """Display cache information."""
    cache_info = get_cache_info()
    print("Cache Information:")
    for key, value in cache_info.items():
        print(f"  {key}: {value}")


def clear_experiment_cache():
    """Clear the experiment cache."""
    try:
        clear_cache()
        print("Cache cleared successfully!")
    except Exception as e:
        print(f"Error clearing cache: {e}")
        sys.exit(1)


async def main():
    """Main entry point for experiment execution."""
    # Check for cache management commands first
    if len(sys.argv) > 1:
        if sys.argv[1] == "--cache-info":
            show_cache_info()
            return
        elif sys.argv[1] == "--cache-clear":
            clear_experiment_cache()
            return

    # Regular experiment execution
    if len(sys.argv) < 3 or sys.argv[1] != "-c":
        print("Usage:")
        print("  python -m src.hex_machina.experiments -c <config_file>")
        print("  python -m src.hex_machina.experiments --cache-info")
        print("  python -m src.hex_machina.experiments --cache-clear")
        print("  python -m src.hex_machina.experiments -c <config_file> --no-cache")
        sys.exit(1)

    config_path = sys.argv[2]

    # Check for --no-cache flag
    enable_caching = True
    if "--no-cache" in sys.argv:
        enable_caching = False
        print("Caching disabled for this experiment run")

    if not Path(config_path).exists():
        print(f"Config file not found: {config_path}")
        sys.exit(1)

    # Load environment variables first
    load_environment()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        # Load configuration
        print(f"Loading experiment configuration from: {config_path}")
        config = load_experiment_config(config_path)

        # Create and run experiment with caching preference
        print(f"Starting experiment: {config.name}")
        runner = ExperimentRunner(enable_caching=enable_caching)

        results = await runner.run_experiment(config)

        print("Experiment completed successfully!")
        print(f"Results: {results}")

    except Exception as e:
        print(f"Experiment failed: {e}")
        logging.exception("Experiment execution failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
