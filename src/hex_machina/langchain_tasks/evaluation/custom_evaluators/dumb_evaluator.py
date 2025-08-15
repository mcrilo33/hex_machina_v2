"""Dumb evaluator that always returns True for testing purposes."""

from typing import Any, Dict


def dumb_evaluator(run: Dict[str, Any], example: Dict[str, Any]) -> bool:
    """A simple evaluator that always returns True for testing dataset splits.

    Args:
        run: The run data from LangSmith (not used in this evaluator)
        example: The example to evaluate (not used in this evaluator)

    Returns:
        Always True for testing purposes
    """
    return True


def dumb_evaluator_apply(examples: list[Dict[str, Any]]) -> list[bool]:
    """Apply the dumb evaluator to a list of examples.

    Args:
        examples: List of examples to evaluate

    Returns:
        List of True values (one for each example)
    """
    return [True for _ in examples]
