"""
Evaluator factory for creating evaluator functions based on YAML configuration.

This module provides a factory pattern for creating evaluator functions
that can be used with LangSmith's aevaluate.
"""

import logging
from typing import Callable

from ..evaluation.registry import evaluator_registry
from .config_models import EvaluatorConfig


class EvaluatorFactory:
    """Factory for creating evaluator functions from configuration."""

    def __init__(self):
        """Initialize the evaluator factory."""
        self._logger = logging.getLogger(
            "langchain_tasks.experiments.evaluator_factory"
        )

    def create_evaluator(self, config: EvaluatorConfig) -> Callable:
        """Create evaluator instance from configuration."""
        try:
            # Get evaluator class from registry
            evaluator_class = evaluator_registry.get_evaluator_class(config.type)

            # Create instance with parameters
            parameters = config.parameters or {}
            evaluator_instance = evaluator_class(**parameters)

            # Return wrapper that matches expected interface
            return self._create_evaluator_wrapper(evaluator_instance, config)

        except Exception as e:
            raise ValueError(f"Failed to create evaluator '{config.type}': {e}")

    def _create_evaluator_wrapper(
        self, evaluator_instance, config: EvaluatorConfig
    ) -> Callable:
        """Create wrapper that converts between interfaces."""

        def evaluator_wrapper(run, example):
            # Extract data from run/example
            prediction = run.outputs.get("result", "")
            reference = (
                example.outputs.get("reference", "") if example.outputs else None
            )
            input_data = run.inputs

            # Handle empty or invalid inputs for JSON evaluators
            if config.type == "JsonEqualityEvaluator":
                # Ensure prediction is valid JSON
                if not prediction or not prediction.strip():
                    return {
                        "score": False,
                        "reasoning": "Empty prediction - cannot evaluate JSON equality",
                        "error": "Empty prediction string",
                    }

                # Ensure reference is valid JSON if provided
                if reference and not reference.strip():
                    reference = None

                # Try to validate JSON format
                try:
                    import json

                    json.loads(prediction)
                    if reference:
                        json.loads(reference)
                except json.JSONDecodeError as e:
                    return {
                        "score": False,
                        "reasoning": f"Invalid JSON format: {str(e)}",
                        "error": f"JSON decode error: {str(e)}",
                    }

            # Call the evaluator
            if hasattr(evaluator_instance, "evaluate_strings"):
                try:
                    result = evaluator_instance.evaluate_strings(
                        prediction=prediction, reference=reference, input=input_data
                    )
                except Exception as e:
                    return {
                        "score": False,
                        "reasoning": f"Evaluation failed: {str(e)}",
                        "error": str(e),
                    }
            elif hasattr(evaluator_instance, "evaluate"):
                try:
                    result = evaluator_instance.evaluate(
                        prediction=prediction, reference=reference, input=input_data
                    )
                except Exception as e:
                    return {
                        "score": False,
                        "reasoning": f"Evaluation failed: {str(e)}",
                        "error": str(e),
                    }
            else:
                raise ValueError(
                    f"Evaluator {config.type} has no known evaluation method"
                )

            return result

        return evaluator_wrapper


# Global factory instance
evaluator_factory = EvaluatorFactory()
