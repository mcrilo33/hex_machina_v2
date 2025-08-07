"""LangChain output parsers for content completeness evaluation."""

import json
import logging
from typing import List, Optional

from langchain_core.output_parsers import BaseOutputParser
from pydantic import BaseModel, Field, ValidationError


class CompletenessEvaluationOutput(BaseModel):
    """Structured output from LLM completeness evaluation."""

    is_complete: bool = Field(..., description="Whether the article is complete")
    detected_issues: List[str] = Field(
        default_factory=list, description="List of detected issues"
    )


class ContentCompletenessOutputParser(BaseOutputParser[CompletenessEvaluationOutput]):
    """Parser for content completeness evaluation LLM outputs."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the parser.

        Args:
            logger: Optional logger instance.
        """
        super().__init__()
        self._logger = logger or logging.getLogger(self.__class__.__name__)

    def parse(self, text: str) -> CompletenessEvaluationOutput:
        """Parse LLM response text into structured output.

        Args:
            text: Raw text response from LLM.

        Returns:
            CompletenessEvaluationOutput: Parsed evaluation result.

        Raises:
            ValueError: If parsing fails.
        """
        try:
            # Clean the text - remove any markdown formatting
            cleaned_text = self._clean_llm_response(text)

            # Parse JSON
            parsed_data = json.loads(cleaned_text)

            # Validate and convert to CompletenessEvaluationOutput
            return CompletenessEvaluationOutput(**parsed_data)

        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse JSON from LLM response: {e}")
            self._logger.debug(f"Raw response: {text}")
            raise ValueError(f"Invalid JSON in LLM response: {e}")

        except ValidationError as e:
            self._logger.error(f"Failed to validate evaluation output: {e}")
            self._logger.debug(f"Parsed data: {parsed_data}")
            raise ValueError(f"Invalid evaluation output structure: {e}")

    def _clean_llm_response(self, text: str) -> str:
        """Clean LLM response text for JSON parsing.

        Args:
            text: Raw LLM response text.

        Returns:
            str: Cleaned text ready for JSON parsing.
        """
        # Remove markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                text = text[start:end].strip()

        # Remove any leading/trailing whitespace and newlines
        text = text.strip()

        # Handle cases where LLM adds explanatory text before/after JSON
        # Look for the first { and last }
        start_brace = text.find("{")
        end_brace = text.rfind("}")

        if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
            text = text[start_brace : end_brace + 1]

        return text

    def get_format_instructions(self) -> str:
        """Get format instructions for the LLM.

        Returns:
            str: Format instructions.
        """
        return """You must respond with a valid JSON object containing the following fields:

{
    "is_complete": true/false,
    "detected_issues": ["list", "of", "issues"]
}

Respond only with the JSON object, no additional text or markdown formatting."""
