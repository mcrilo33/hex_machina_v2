"""
Custom evaluator for content quality evaluation.

This evaluator checks if the content is marked as of bad quality based on the LLM output.
"""

import json
import logging
from typing import Any


def bad_quality(run: Any, example: Any) -> bool:
    """
    Evaluate if the example is of bad quality.

    Args:
        run: The run object containing the LLM output (not used in this evaluator)
        example: The example object containing the output data

    Returns:
        True if the article is complete, False otherwise
    """
    logger = logging.getLogger(__name__)

    try:
        example = example.__dict__
        # Check if the example has the expected structure
        if "outputs" not in example:
            logger.warning("Example does not have outputs attribute")
            return True

        if "generations" not in example["outputs"]:
            logger.warning("Example outputs does not contain 'generations' field")
            return True

        generations = example["outputs"]["generations"]

        # Check if generations is a list and has content
        if not isinstance(generations, list) or len(generations) == 0:
            logger.warning("Generations is not a list or is empty")
            return True

        # Get the first generation
        first_generation = generations[0]
        if not isinstance(first_generation, list) or len(first_generation) == 0:
            logger.warning("First generation is not a list or is empty")
            return True

        # Get the text from the first generation item
        generation_item = first_generation[0]
        if not isinstance(generation_item, dict):
            logger.warning("Generation item is not a dictionary")
            return True

        if "text" not in generation_item:
            logger.warning("Generation item does not contain 'text' field")
            return True

        text_content = generation_item["text"]

        # Parse the JSON content
        try:
            if "```json" in text_content:
                # Extract from markdown
                start = text_content.find("```json") + 7
                end = text_content.rfind("```")
                json_text = text_content[start:end].strip()
            else:
                json_text = text_content.strip()
            parsed_content = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from text: {e}")
            return True

        # Check if the parsed content has the is_complete field
        if "is_high_quality" not in parsed_content:
            logger.warning("Parsed content does not contain 'is_complete' field")
            return True

        # Get the is_high_quality value
        is_high_quality = parsed_content["is_high_quality"]

        # Check if it's a boolean and True
        if isinstance(is_high_quality, bool):
            result = not is_high_quality
            logger.debug(f"Content quality: {result}")
            return result
        else:
            logger.warning(f"is_high_quality is not a boolean: {type(is_complete)}")
            return True

    except Exception as e:
        logger.error(f"Error during content quality evaluation: {e}")
        return True
