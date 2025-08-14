"""
Custom evaluator for article completeness schema validation.

This evaluator wraps the JsonSchemaEvaluator and provides the expected schema
for article completeness evaluation.
"""

import logging
from typing import Any, Dict

from langchain.evaluation.parsing.json_schema import JsonSchemaEvaluator


def article_completeness_schema_evaluator(run: Any, example: Any) -> Dict[str, Any]:
    """
    Evaluate if the LLM output matches the expected article completeness schema.

    Args:
        run: The run object containing the LLM output
        example: The example object containing input data

    Returns:
        Dictionary with validation results
    """
    logger = logging.getLogger(__name__)

    try:
        # Define the expected schema for article completeness
        expected_schema = """{
            "type": "object",
            "properties": {
                "is_complete": {
                    "type": "boolean",
                    "description": "Whether the article is complete"
                },
                "reasons": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "content_truncated",
                            "paywall_content",
                            "error_page",
                            "minimal_content"
                        ]
                    },
                    "description": "List of reasons for incompleteness"
                }
            },
            "required": ["is_complete", "reasons"]
        }"""

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

        # Create JsonSchemaEvaluator instance
        evaluator = JsonSchemaEvaluator()

        # Evaluate the prediction against the schema
        result = evaluator.evaluate_strings(
            prediction=prediction, reference=str(expected_schema)
        )

        # Extract the score (True if valid, False if invalid)
        score = result.get("score", False)

        # Get additional validation details
        comment = result.get("reasoning", "")

        logger.info(f"Schema validation result: {score}, Reasoning: {comment}")

        return {
            "score": score,
            "comment": comment,
            "schema_valid": score,
            "prediction": (
                prediction[:200] + "..." if len(prediction) > 200 else prediction
            ),
        }

    except Exception as e:
        logger.error(f"Error during schema validation: {e}")
        return {
            "score": False,
            "comment": f"Schema validation failed: {str(e)}",
            "error": str(e),
        }
