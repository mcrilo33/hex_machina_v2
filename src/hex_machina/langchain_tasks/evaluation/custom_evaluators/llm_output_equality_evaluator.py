"""
Custom evaluator for LLM output JSON equality validation.

This evaluator wraps the JsonEqualityEvaluator and compares the LLM output
against the reference field in the example data.
"""

import logging
from typing import Any, Dict

from langchain.evaluation.parsing.base import JsonEqualityEvaluator


def llm_output_equality_evaluator(run: Any, example: Any) -> Dict[str, Any]:
    """
    Evaluate if the LLM output exactly matches the reference JSON from the example.

    Args:
        run: The run object containing the LLM output
        example: The example object containing reference data

    Returns:
        Dictionary with equality validation results
    """
    logger = logging.getLogger(__name__)

    try:
        # Get the prediction from the run
        if hasattr(run, "outputs") and "content" in run.outputs:
            prediction = str(run.outputs["content"])
        else:
            logger.warning("Could not find output in run")
            return {
                "score": False,
                "comment": "No output found in run",
                "error": "Missing output field",
            }

        # Get the reference from the example
        reference = str(example.outputs["generations"][0][0]["text"])

        # Create JsonEqualityEvaluator instance
        evaluator = JsonEqualityEvaluator()

        # Evaluate the prediction against the reference
        result = evaluator.evaluate_strings(prediction=prediction, reference=reference)

        score = result.get("score", False)

        logger.info(f"Equality validation result: {score}")

        return {
            "score": score,
            "exact_match": score,
            "prediction": (
                prediction[:200] + "..." if len(prediction) > 200 else prediction
            ),
            "reference": reference[:200] + "..." if len(reference) > 200 else reference,
        }

    except Exception as e:
        logger.error(f"Error during equality validation: {e}")
        return {
            "score": False,
            "error": str(e),
        }
