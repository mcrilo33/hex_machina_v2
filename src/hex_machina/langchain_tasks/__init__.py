"""
LangChain Tasks - A modular system for building, executing, and evaluating LangChain applications.

This package provides:
- Task building from YAML configuration
- Runnable registry for custom and built-in components
- Dataset generation and management
- Evaluation system using LangSmith
- Experiment execution with multiple variations
"""

from .builder import TaskBuilder
from .config import EvaluationConfig, ExperimentConfig, StepConfig, TaskConfig
from .datasets import DatasetGenerator, StepDataset, StepDatasetManager
from .evaluation import EvaluationRunner, EvaluatorRegistry, evaluator_registry
from .experiments import ExperimentRunner
from .registry import RunnableRegistry

__version__ = "0.1.0"

__all__ = [
    # Core components
    "TaskBuilder",
    "RunnableRegistry",
    # Configuration models
    "TaskConfig",
    "StepConfig",
    "ExperimentConfig",
    "EvaluationConfig",
    # Dataset management
    "DatasetGenerator",
    "StepDataset",
    "StepDatasetManager",
    # Evaluation system
    "EvaluationRunner",
    "EvaluatorRegistry",
    "evaluator_registry",
    # Experiment system
    "ExperimentRunner",
]
