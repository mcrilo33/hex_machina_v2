"""Generic JSON output parser."""

import json
from typing import Any, Dict, List, Optional

from src.hex_machina.core import TaskException

from .base import BaseOutputParser


class JSONOutputParser(BaseOutputParser):
    """Generic JSON output parser with validation."""

    def __init__(
        self,
        name: str = "json_parser",
        required_fields: Optional[List[str]] = None,
        optional_fields: Optional[List[str]] = None,
        field_types: Optional[Dict[str, type]] = None,
    ):
        """Initialize JSON parser.

        Args:
            name: Parser name
            required_fields: List of required field names
            optional_fields: List of optional field names
            field_types: Dictionary mapping field names to expected types
        """
        super().__init__(name)
        self.required_fields = required_fields or []
        self.optional_fields = optional_fields or []
        self.field_types = field_types or {}

    def parse(self, raw_output: str) -> Dict[str, Any]:
        """Parse raw output as JSON.

        Args:
            raw_output: Raw output from LLM

        Returns:
            Parsed JSON dictionary

        Raises:
            TaskException: If parsing fails
        """
        try:
            # Try to parse as JSON
            parsed = json.loads(raw_output)

            # Validate the parsed output
            if not self.validate(parsed):
                raise TaskException("Parsed output validation failed")

            return parsed

        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse JSON: {e}")
            self._logger.error(f"Raw output: {raw_output}")
            raise TaskException(f"Invalid JSON format: {e}")

        except Exception as e:
            self._logger.error(f"Unexpected error parsing JSON: {e}")
            raise TaskException(f"JSON parsing failed: {e}")

    def validate(self, parsed_output: Dict[str, Any]) -> bool:
        """Validate parsed JSON output.

        Args:
            parsed_output: Parsed output to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check if it's a dictionary
            if not isinstance(parsed_output, dict):
                self._logger.error("Parsed output is not a dictionary")
                return False

            # Check required fields
            for field in self.required_fields:
                if field not in parsed_output:
                    self._logger.error(f"Missing required field: {field}")
                    return False

            # Check field types
            for field, expected_type in self.field_types.items():
                if field in parsed_output:
                    if not isinstance(parsed_output[field], expected_type):
                        self._logger.error(
                            f"Field {field} has wrong type. "
                            f"Expected {expected_type}, got {type(parsed_output[field])}"
                        )
                        return False

            return True

        except Exception as e:
            self._logger.error(f"Validation error: {e}")
            return False

    def get_parser_info(self) -> Dict[str, Any]:
        """Get parser information with validation rules."""
        info = super().get_parser_info()
        info.update(
            {
                "required_fields": self.required_fields,
                "optional_fields": self.optional_fields,
                "field_types": {k: v.__name__ for k, v in self.field_types.items()},
            }
        )
        return info
