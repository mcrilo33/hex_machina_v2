"""
Pydantic models for YAML-based experiment configuration.

This module provides models for defining experiments declaratively in YAML,
including task variations with multiple values and evaluation configurations.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvaluatorParameter(BaseModel):
    """Configuration for evaluator parameters."""

    name: str = Field(..., description="Parameter name")
    value: Any = Field(..., description="Parameter value")
    description: Optional[str] = Field(
        default=None, description="Parameter description"
    )


class EvaluatorConfig(BaseModel):
    """Configuration for a single evaluator."""

    name: str = Field(..., description="Name of the evaluator")
    type: str = Field(..., description="Type of evaluator (e.g., 'custom_function')")
    description: Optional[str] = Field(
        default=None, description="Evaluator description"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Evaluator parameters"
    )


class StepConfig(BaseModel):
    """Configuration for a single step in a task."""

    name: str = Field(..., description="Name of the step")
    runnable: str = Field(..., description="Name of the runnable to use")
    dataset: bool = Field(
        default=False, description="Whether to create a dataset for this step"
    )
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Configuration for the runnable"
    )

    def get_multi_value_fields(self) -> Dict[str, List[Any]]:
        """Get fields with multiple values for variation generation."""
        multi_value_fields = {}
        if self.config:
            for field_name, field_value in self.config.items():
                if isinstance(field_value, list) and len(field_value) > 1:
                    multi_value_fields[field_name] = field_value
        return multi_value_fields


class TaskConfig(BaseModel):
    """Configuration for a task that can have variations."""

    name: str = Field(..., description="Name of the task")
    description: Optional[str] = Field(default=None, description="Task description")
    steps: List[StepConfig] = Field(..., description="List of steps to execute")
    dataset: bool = Field(
        default=False, description="Whether to create a task-level dataset"
    )

    def get_all_multi_value_fields(self) -> Dict[str, List[Any]]:
        """Get all multi-value fields from all steps."""
        all_multi_values = {}
        for step in self.steps:
            step_multi_values = step.get_multi_value_fields()
            for field_name, values in step_multi_values.items():
                step_key = f"{step.name}.{field_name}"
                all_multi_values[step_key] = values
        return all_multi_values


class ExperimentSettings(BaseModel):
    """Global settings for experiments."""

    experiment_prefix: str = Field(
        default="experiment", description="Prefix for experiment names"
    )
    save_results: bool = Field(
        default=True, description="Whether to save results to LangSmith"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Global metadata for all experiments"
    )


class ExperimentConfiguration(BaseModel):
    """Complete experiment configuration with task variations and evaluation."""

    name: str = Field(..., description="Configuration name")
    description: Optional[str] = Field(
        default=None, description="Configuration description"
    )

    # Task configuration (can have multiple values for variations)
    task: TaskConfig = Field(..., description="Base task configuration")

    # Evaluation configuration with target datasets
    evaluations: Dict[str, Any] = Field(
        default_factory=dict, description="Evaluation configuration for steps and task"
    )

    # Global settings
    settings: Optional[ExperimentSettings] = Field(
        default_factory=ExperimentSettings, description="Global experiment settings"
    )

    def generate_task_variations(self) -> List[TaskConfig]:
        """Generate all possible task variations based on multi-value fields."""
        import itertools

        # Get all multi-value fields from all steps
        multi_value_fields = self.task.get_all_multi_value_fields()

        if not multi_value_fields:
            # No variations, return original task
            return [self.task]

        # Generate all combinations
        field_names = list(multi_value_fields.keys())
        field_values = list(multi_value_fields.values())

        variations = []
        for combination in itertools.product(*field_values):
            # Create a copy of the task
            variation = self.task.model_copy(deep=True)
            variation.name = f"{self.task.name}_variation_{len(variations) + 1}"

            # Apply the combination to the appropriate step and field
            for i, (field_name, value) in enumerate(zip(field_names, combination)):
                step_name, config_field = field_name.split(".", 1)

                # Find the step and update its config
                for step in variation.steps:
                    if step.name == step_name:
                        if step.config is None:
                            step.config = {}
                        step.config[config_field] = value
                        break

            variations.append(variation)

        return variations

    def get_experiment_names(self) -> List[str]:
        """Get list of experiment names."""
        return [f"variation_{i+1}" for i in range(len(self.generate_task_variations()))]

    def get_variation_count(self) -> int:
        """Get the number of variations that will be generated."""
        return len(self.generate_task_variations())

    def get_evaluation_config(
        self, step_name: Optional[str] = None
    ) -> List[EvaluatorConfig]:
        """Get evaluation configuration for a specific step or task level."""
        if step_name:
            # Step-level evaluation
            step_evaluations = self.evaluations.get("steps", {}).get(step_name, {})
            if isinstance(step_evaluations, dict) and "evaluators" in step_evaluations:
                step_evaluations = step_evaluations["evaluators"]
            else:
                step_evaluations = []
        else:
            # Task-level evaluation
            task_evaluations = self.evaluations.get("task", {})
            if isinstance(task_evaluations, dict) and "evaluators" in task_evaluations:
                step_evaluations = task_evaluations["evaluators"]
            else:
                step_evaluations = []

        # Convert to EvaluatorConfig objects
        evaluators = []
        if isinstance(step_evaluations, list):
            for eval_config in step_evaluations:
                if isinstance(eval_config, dict):
                    evaluators.append(EvaluatorConfig(**eval_config))
                elif isinstance(eval_config, EvaluatorConfig):
                    evaluators.append(eval_config)

        return evaluators

    def get_target_datasets_for_step(self, step_name: str) -> List[str]:
        """Get target datasets for a specific step."""
        import logging

        logger = logging.getLogger("langchain_tasks.experiments.config_models")

        step_evaluations = self.evaluations.get("steps", {}).get(step_name, [])
        logger.info(
            f"🔍 Getting target datasets for step '{step_name}': {step_evaluations}"
        )

        if isinstance(step_evaluations, dict):
            target_datasets = step_evaluations.get("target_datasets", [])
            logger.info(
                f"📊 Step '{step_name}' target datasets (dict): {target_datasets}"
            )
            return target_datasets
        elif isinstance(step_evaluations, list):
            # If it's a list of evaluators, look for target_datasets in the first one
            if step_evaluations and isinstance(step_evaluations[0], dict):
                target_datasets = step_evaluations[0].get("target_datasets", [])
                logger.info(
                    f"📊 Step '{step_name}' target datasets (list): {target_datasets}"
                )
                return target_datasets
        logger.info(f"📊 Step '{step_name}' no target datasets found")
        return []

    def get_target_datasets_for_task(self) -> List[str]:
        """Get target datasets for task-level evaluation."""
        import logging

        logger = logging.getLogger("langchain_tasks.experiments.config_models")

        task_evaluations = self.evaluations.get("task", [])
        logger.info(f"🔍 Getting task-level target datasets: {task_evaluations}")

        if isinstance(task_evaluations, dict):
            target_datasets = task_evaluations.get("target_datasets", [])
            logger.info(f"📊 Task-level target datasets (dict): {target_datasets}")
            return target_datasets
        elif isinstance(task_evaluations, list):
            # If it's a list of evaluators, look for target_datasets in the first one
            if task_evaluations and isinstance(task_evaluations[0], dict):
                target_datasets = task_evaluations[0].get("target_datasets", [])
                logger.info(f"📊 Task-level target datasets (list): {target_datasets}")
                return target_datasets
        logger.info("📊 Task-level no target datasets found")
        return []
