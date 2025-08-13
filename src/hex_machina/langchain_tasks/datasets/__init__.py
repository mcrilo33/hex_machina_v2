"""
Dataset generation module for LangChain tasks.

This module provides:
- Step-specific dataset generation
- LangSmith dataset integration
- Configuration-driven dataset creation
- Automatic dataset management during task execution
"""

from .generator import DatasetGenerator
from .models import StepDataset
from .step_manager import StepDatasetManager

__all__ = [
    "DatasetGenerator",
    "StepDatasetManager",
    "StepDataset",
]
