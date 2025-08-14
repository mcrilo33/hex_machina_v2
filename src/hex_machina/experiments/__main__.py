"""
Command-line interface for running experiments.

Usage:
    poetry run python -m src.hex_machina.experiments -c <config_file>
"""

import asyncio
import logging
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

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

        return ExperimentConfig(**config_data)
    except Exception as e:
        print(f"Error loading experiment config: {e}")
        sys.exit(1)


async def main():
    """Main entry point for experiment execution."""
    if len(sys.argv) < 3 or sys.argv[1] != "-c":
        print("Usage: python -m src.hex_machina.experiments -c <config_file>")
        sys.exit(1)

    config_path = sys.argv[2]

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

        # Create and run experiment
        print(f"Starting experiment: {config.name}")
        runner = ExperimentRunner()

        results = await runner.run_experiment(config)

        print("Experiment completed successfully!")
        print(f"Results: {results}")

    except Exception as e:
        print(f"Experiment failed: {e}")
        logging.exception("Experiment execution failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
