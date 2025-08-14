"""
YAML runner for experiments.

This module handles loading experiment configurations from YAML files
and executing them using the ExperimentRunner.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Union

import yaml

# Load environment variables from .env files
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass

from .config_models import ExperimentConfig
from .runner import ExperimentRunner


class ExperimentYAMLRunner:
    """Runner for executing experiments from YAML configuration files."""

    def __init__(self):
        """Initialize the YAML runner."""
        self.runner = ExperimentRunner()
        self._logger = logging.getLogger(__name__)

        self._logger.info("ExperimentYAMLRunner initialized")

    def load_experiment_config(self, config_path: Union[str, Path]) -> ExperimentConfig:
        """Load experiment configuration from YAML file.

        Args:
            config_path: Path to the YAML configuration file

        Returns:
            Loaded experiment configuration

        Raises:
            FileNotFoundError: If the config file doesn't exist
            yaml.YAMLError: If the YAML is invalid
            ValueError: If the configuration is invalid
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Experiment config file not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            self._logger.info(f"Loaded experiment config from: {config_path}")

            # Resolve environment variables in config values (same as CLI)
            resolved_yaml_data = self._resolve_env_vars(yaml_data)

            # Validate and create ExperimentConfig
            config = ExperimentConfig(**resolved_yaml_data)

            self._logger.info(f"Experiment config validated: {config.name}")
            return config

        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in {config_path}: {e}")
        except Exception as e:
            raise ValueError(f"Invalid experiment configuration in {config_path}: {e}")

    def _resolve_env_vars(self, obj):
        """Recursively resolve environment variables in config values (same as CLI)."""
        import os

        if isinstance(obj, dict):
            return {k: self._resolve_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            env_var = obj[2:-1]  # Remove ${ and }
            return os.getenv(env_var, obj)  # Return original if env var not found
        else:
            return obj

    async def run_experiment_from_yaml(
        self, config_path: Union[str, Path]
    ) -> Dict[str, Any]:
        """Run an experiment from a YAML configuration file.

        Args:
            config_path: Path to the YAML configuration file

        Returns:
            Experiment results
        """
        # Load configuration
        config = self.load_experiment_config(config_path)

        # Run experiment
        return await self.runner.run_experiment(config)

    def run_experiment_from_yaml_sync(
        self, config_path: Union[str, Path]
    ) -> Dict[str, Any]:
        """Synchronous version of run_experiment_from_yaml.

        Args:
            config_path: Path to the YAML configuration file

        Returns:
            Experiment results
        """
        import asyncio

        try:
            # Get the current event loop or create a new one
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run the async function
            return loop.run_until_complete(self.run_experiment_from_yaml(config_path))

        except Exception as e:
            self._logger.error(f"Failed to run experiment: {e}")
            raise
