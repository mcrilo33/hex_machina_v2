"""
Configuration models for experiments with evaluation support.

This module defines the data models for experiment configuration,
following the new structure where experiments use existing TaskConfigs
and evaluate them using LangSmith.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ..langchain_tasks.config.models import TaskConfig


class EvaluatorConfig(BaseModel):
    """Configuration for an evaluator in an experiment."""

    name: str = Field(..., description="Name of the evaluator")
    type: str = Field(..., description="Type of evaluator")
    description: str = Field(..., description="Description of what the evaluator does")
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration for the evaluator (model, temperature, criteria, etc.)",
    )


class ExperimentConfig(BaseModel):
    """Configuration for running experiments with task evaluation."""

    name: str = Field(..., description="Name of the experiment")
    description: str = Field(..., description="Description of the experiment")
    target_dataset: str = Field(..., description="Reference to existing dataset")
    task: TaskConfig = Field(..., description="Task configuration to evaluate")
    evaluators: List[EvaluatorConfig] = Field(..., description="List of evaluators")
    split: Optional[Union[str, List[str]]] = Field(
        default=None,
        description="Dataset split(s) to use for evaluation. Can be a single split name or list of splits (e.g., 'test', ['test', 'training'])",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional experiment metadata"
    )
