"""Core module for Hex Machina v2.

This module provides the foundational base classes and utilities used across
all other modules in the project.
"""

from .base import (
    BaseConfig,
    BaseEvaluator,
    BaseModule,
    BaseTask,
    BaseWorkflow,
    EvaluationResult,
    TaskInput,
    TaskOutput,
    WorkflowResult,
)
from .config import ConfigManager
from .exceptions import (
    ConfigurationException,
    EvaluationException,
    HexMachinaException,
    TaskException,
    WorkflowException,
)

__all__ = [
    # Base classes
    "BaseModule",
    "BaseConfig",
    "BaseTask",
    "BaseWorkflow",
    "BaseEvaluator",
    # Data models
    "TaskInput",
    "TaskOutput",
    "WorkflowResult",
    "EvaluationResult",
    # Configuration
    "ConfigManager",
    # Exceptions
    "HexMachinaException",
    "ConfigurationException",
    "TaskException",
    "WorkflowException",
    "EvaluationException",
]
