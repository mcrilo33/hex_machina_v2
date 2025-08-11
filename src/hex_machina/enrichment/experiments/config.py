"""
Configuration loader for experiments.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class TaskConfig(BaseModel):
    """Configuration for a single task run."""

    name: str
    description: str
    config: Dict[str, Any]


class ComparisonMetrics(BaseModel):
    """Metrics for comparing experiment results."""

    primary: str
    secondary: List[str]
    threshold: float = 0.8


class ExperimentSettings(BaseModel):
    """Settings for experiment execution."""

    max_concurrent_runs: int = 3
    timeout_per_run: int = 300
    save_intermediate_results: bool = True


class ExperimentConfig(BaseModel):
    """Complete experiment configuration."""

    experiment_name: str
    description: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Evaluation settings
    evaluation_dataset: str
    evaluation_split: Optional[str] = None
    evaluators: List[str]

    # Task configurations to test
    task_configs: List[TaskConfig]

    # Comparison settings
    comparison_metrics: ComparisonMetrics

    # Experiment settings
    settings: ExperimentSettings = Field(default_factory=ExperimentSettings)


class ExperimentConfigLoader:
    """Loader for experiment configuration files."""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize with config directory path."""
        if config_dir is None:
            # Default to config/experiments/
            config_dir = (
                Path(__file__).parent.parent.parent.parent.parent
                / "config"
                / "experiments"
            )

        self.config_dir = Path(config_dir)

    def list_experiments(self) -> List[str]:
        """List all available experiment configurations."""
        if not self.config_dir.exists():
            return []

        experiments = []
        for file_path in self.config_dir.glob("*.yaml"):
            experiments.append(file_path.stem)

        return sorted(experiments)

    def load_experiment(self, experiment_name: str) -> ExperimentConfig:
        """Load experiment configuration by name."""
        config_path = self.config_dir / f"{experiment_name}.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Experiment config not found: {config_path}")

        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)

        return ExperimentConfig(**config_data)

    def validate_experiment(self, config: ExperimentConfig) -> List[str]:
        """Validate experiment configuration and return list of errors."""
        errors = []

        # Check required fields
        if not config.experiment_name:
            errors.append("experiment_name is required")

        if not config.evaluation_dataset:
            errors.append("evaluation_dataset is required")

        if not config.evaluators:
            errors.append("evaluators list cannot be empty")

        if not config.task_configs:
            errors.append("task_configs list cannot be empty")

        # Check for duplicate task config names
        task_names = [tc.name for tc in config.task_configs]
        if len(task_names) != len(set(task_names)):
            errors.append("task_config names must be unique")

        # Validate task configurations
        for task_config in config.task_configs:
            if not task_config.config.get("model"):
                errors.append(f"Task config '{task_config.name}' must specify a model")

            if "temperature" not in task_config.config:
                errors.append(
                    f"Task config '{task_config.name}' must specify temperature"
                )

            if "max_tokens" not in task_config.config:
                errors.append(
                    f"Task config '{task_config.name}' must specify max_tokens"
                )

        return errors
