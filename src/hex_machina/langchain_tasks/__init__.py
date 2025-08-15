"""
LangChain Tasks - A framework for building and running LangChain-based tasks.

This package provides a simple way to define, configure, and execute
LangChain tasks and experiments from YAML configuration files.
"""

from .builder import TaskBuilder
from .cache_utils import (
    clear_cache,
    get_cache_info,
    setup_default_cache,
    setup_sqlite_cache,
)
from .cli import main
from .config.models import (
    EvaluationConfig,
    ExperimentConfig,
    StepConfig,
    TaskConfig,
)
from .datasets import StepDatasetManager
from .evaluation.registry import EvaluatorRegistry
from .registry import RunnableRegistry

__version__ = "0.1.0"

__all__ = [
    "TaskBuilder",
    "main",
    "EvaluationConfig",
    "ExperimentConfig",
    "StepConfig",
    "TaskConfig",
    "StepDatasetManager",
    "EvaluatorRegistry",
    "RunnableRegistry",
    "setup_sqlite_cache",
    "setup_default_cache",
    "clear_cache",
    "get_cache_info",
]
