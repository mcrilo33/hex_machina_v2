"""
Dataset management for LangChain tasks.

This module provides functionality for creating and managing datasets
for step-range evaluations.
"""

from .annotation_manager import AnnotationManager
from .annotation_models import AnnotationConfig, AnnotationField, AnnotationSession
from .generator import DatasetGenerator
from .models import DatasetDefinition
from .split_creator import create_split_with_evaluator, delete_split
from .step_manager import StepDatasetManager


def run_interactive_annotation(config_path):
    """Run an interactive annotation session.

    Args:
        config_path: Path to the annotation configuration file
    """
    manager = AnnotationManager()
    manager.run_annotation_session(str(config_path))


__all__ = [
    "DatasetGenerator",
    "DatasetDefinition",
    "StepDatasetManager",
    "create_split_with_evaluator",
    "delete_split",
    "AnnotationManager",
    "AnnotationConfig",
    "AnnotationSession",
    "AnnotationField",
    "run_interactive_annotation",
]
