"""
Configuration models for LangChain tasks with evaluation support.

This module defines the data models for task configuration, experiment configuration,
and evaluation configuration, following LangSmith's philosophy.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvaluationConfig(BaseModel):
    """Configuration for evaluation criteria and parameters."""

    name: str = Field(..., description="Name of the evaluator")
    criteria: Optional[List[str]] = Field(
        default=None, description="Evaluation criteria (for criteria-based evaluators)"
    )
    reference_dataset: Optional[str] = Field(
        default=None, description="Reference dataset for comparison"
    )
    # Allow any additional hyperparameters
    hyperparameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional evaluator hyperparameters"
    )


class StepConfig(BaseModel):
    """Configuration for a single step in a task."""

    name: str = Field(..., description="Name of the step")
    runnable: str = Field(..., description="Name of the runnable to use")
    inputs: Optional[Dict[str, Any]] = Field(
        default=None, description="Input mapping for this step"
    )
    outputs: Optional[Dict[str, Any]] = Field(
        default=None, description="Output mapping for this step"
    )
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Configuration for the runnable (cache, fallbacks, retry, etc.)",
    )
    configurable: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Configurable fields for runtime overrides"
    )
    dataset: Optional[bool] = Field(
        default=False, description="Whether to create a dataset for this step"
    )
    # Support for multiple values (experiments)
    multi_value_fields: Optional[Dict[str, List[Any]]] = Field(
        default=None, description="Internal: fields with multiple values"
    )

    def get_multi_value_fields(self) -> Dict[str, List[Any]]:
        """Get fields with multiple values for experiment generation."""
        multi_value_fields = {}
        if self.config:
            for field_name, field_value in self.config.items():
                if isinstance(field_value, list) and len(field_value) > 1:
                    multi_value_fields[field_name] = field_value
        return multi_value_fields


class TaskConfig(BaseModel):
    """Configuration for a complete task."""

    name: str = Field(..., description="Name of the task")
    description: Optional[str] = Field(
        default=None, description="Description of the task"
    )
    steps: List[StepConfig] = Field(..., description="List of steps to execute")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata for the task"
    )
    dataset: Optional[bool] = Field(
        default=False, description="Whether to create a task-level dataset"
    )
    # Online evaluation configuration (future feature)
    online_evaluation: Optional[Dict[str, List[EvaluationConfig]]] = Field(
        default=None,
        description="Online evaluation configuration for real-time evaluation",
    )


class ExperimentConfig(BaseModel):
    """Configuration for running experiments with multiple task variations."""

    name: str = Field(..., description="Name of the experiment")
    description: Optional[str] = Field(
        default=None, description="Description of the experiment"
    )
    task: TaskConfig = Field(..., description="Base task configuration")
    evaluations: Dict[str, Any] = Field(
        default_factory=dict, description="Evaluation configuration for steps and task"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional experiment metadata"
    )

    def generate_task_variations(self) -> List[TaskConfig]:
        """Generate all possible task variations from multiple values."""
        variations = []

        # Find all fields with multiple values across all steps
        multi_value_fields = {}
        for step in self.task.steps:
            step_multi_values = step.get_multi_value_fields()
            if step_multi_values:
                for field_name, values in step_multi_values.items():
                    step_key = f"{step.name}.{field_name}"
                    multi_value_fields[step_key] = values
                    print(
                        f"🔍 DEBUG: Found multi-value field '{step_key}' with values: {values}"
                    )

        if not multi_value_fields:
            # No variations, return original task
            print("🔍 DEBUG: No multi-value fields found, returning original task")
            return [self.task]

        print(f"🔍 DEBUG: Found {len(multi_value_fields)} multi-value fields")

        # Generate all combinations
        from itertools import product

        # Get all value combinations
        field_names = list(multi_value_fields.keys())
        value_lists = list(multi_value_fields.values())

        print(f"🔍 DEBUG: Field names: {field_names}")
        print(f"🔍 DEBUG: Value lists: {value_lists}")

        for combination in product(*value_lists):
            print(f"🔍 DEBUG: Generating combination: {combination}")
            # Create a new task config with this combination
            new_task = self.task.model_copy(deep=True)

            # Apply the combination values
            for field_name, value in zip(field_names, combination):
                step_name, param_name = field_name.split(".", 1)

                # Find the step and update its config
                for step in new_task.steps:
                    if step.name == step_name:
                        if param_name in step.config:
                            step.config[param_name] = value
                        else:
                            # Add to config if not present
                            step.config[param_name] = value
                        break

            variations.append(new_task)

        print(f"🔍 DEBUG: Generated {len(variations)} variations")
        return variations
