"""
Evaluation module for hex_machina.
"""

from .config import EvaluationConfig
from .evaluation_functions import (
    evaluate_dataset_examples,
    evaluate_workflow_operation,
    list_available_evaluators,
    run_evaluators,
)
from .langsmith_integration import (
    create_evaluation_experiment,
    log_evaluation_result,
    setup_langsmith_environment,
)

__all__ = [
    "evaluate_workflow_operation",
    "evaluate_dataset_examples",
    "run_evaluators",
    "list_available_evaluators",
    "setup_langsmith_environment",
    "create_evaluation_experiment",
    "log_evaluation_result",
    "EvaluationConfig",
]
