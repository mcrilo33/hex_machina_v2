"""
Custom evaluator for article completeness evaluation.

This evaluator checks if the article is marked as complete based on the LLM output.
"""

import json
import logging
from typing import Any, Dict


def article_completeness_evaluator(run: Any, example: Any) -> bool:
    """
    Evaluate if the article is marked as complete.

    Args:
        run: The run object containing the LLM output (not used in this evaluator)
        example: The example object containing the output data

    Returns:
        True if the article is complete, False otherwise
    """
    logger = logging.getLogger(__name__)

    try:
        # Check if the example has the expected structure
        if not hasattr(example, "outputs"):
            logger.warning("Example does not have outputs attribute")
            return False
        
        if "generations" not in example.outputs:
            logger.warning("Example outputs does not contain 'generations' field")
            return False
        
        generations = example.outputs["generations"]
        
        # Check if generations is a list and has content
        if not isinstance(generations, list) or len(generations) == 0:
            logger.warning("Generations is not a list or is empty")
            return False
        
        # Get the first generation
        first_generation = generations[0]
        if not isinstance(first_generation, list) or len(first_generation) == 0:
            logger.warning("First generation is not a list or is empty")
            return False
        
        # Get the text from the first generation item
        generation_item = first_generation[0]
        if not isinstance(generation_item, dict):
            logger.warning("Generation item is not a dictionary")
            return False
        
        if "text" not in generation_item:
            logger.warning("Generation item does not contain 'text' field")
            return False
        
        text_content = generation_item["text"]
        
        # Parse the JSON content
        try:
            parsed_content = json.loads(text_content)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from text: {e}")
            return False
        
        # Check if the parsed content has the is_complete field
        if "is_complete" not in parsed_content:
            logger.warning("Parsed content does not contain 'is_complete' field")
            return False
        
        # Get the is_complete value
        is_complete = parsed_content["is_complete"]
        
        # Check if it's a boolean and True
        if isinstance(is_complete, bool):
            result = is_complete
            logger.debug(f"Article completeness: {result}")
            return result
        else:
            logger.warning(f"is_complete is not a boolean: {type(is_complete)}")
            return False

    except Exception as e:
        logger.error(f"Error during article completeness evaluation: {e}")
        return False
