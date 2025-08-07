"""LangChain output parser wrapper."""

from typing import Any, Dict, Optional

from langchain_core.output_parsers import BaseOutputParser as LangChainBaseOutputParser
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from src.hex_machina.core import TaskException

from .base import BaseOutputParser


class LangChainWrapperParser(BaseOutputParser, Runnable):
    """Wrapper for LangChain output parsers that's compatible with LangChain chains."""

    def __init__(
        self,
        name: str,
        langchain_parser: LangChainBaseOutputParser,
        validation_schema: Optional[Dict[str, Any]] = None,
    ):
        """Initialize LangChain wrapper parser.

        Args:
            name: Parser name
            langchain_parser: LangChain parser to wrap
            validation_schema: Optional validation schema for additional validation
        """
        super().__init__(name, langchain_parser)
        self._validation_schema = validation_schema or {}

    def parse(self, raw_output: str) -> Dict[str, Any]:
        """Parse raw output using LangChain parser.

        Args:
            raw_output: Raw output from LLM

        Returns:
            Parsed output dictionary

        Raises:
            TaskException: If parsing fails
        """
        try:
            # Use LangChain parser
            if self._langchain_parser:
                parsed_result = self._langchain_parser.parse(raw_output)

                # Convert to dictionary if needed
                if isinstance(parsed_result, dict):
                    result = parsed_result
                elif hasattr(parsed_result, "model_dump"):
                    # Pydantic model
                    result = parsed_result.model_dump()
                else:
                    # Other types - convert to dict
                    result = {"result": parsed_result}

                # Additional validation if schema provided
                if self._validation_schema and not self.validate(result):
                    raise TaskException("Output validation failed")

                return result
            else:
                raise TaskException("No LangChain parser configured")

        except Exception as e:
            self._logger.error(f"LangChain parsing failed: {e}")
            raise TaskException(f"LangChain parsing failed: {e}")

    def validate(self, parsed_output: Dict[str, Any]) -> bool:
        """Validate parsed output against schema.

        Args:
            parsed_output: Parsed output to validate

        Returns:
            True if valid, False otherwise
        """
        if not self._validation_schema:
            return True  # No validation schema provided

        try:
            # Check required fields
            required_fields = self._validation_schema.get("required_fields", [])
            for field in required_fields:
                if field not in parsed_output:
                    self._logger.error(f"Missing required field: {field}")
                    return False

            # Check field types
            field_types = self._validation_schema.get("field_types", {})
            for field, expected_type in field_types.items():
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
        """Get parser information with LangChain details."""
        info = super().get_parser_info()
        info.update(
            {
                "langchain_parser_type": self._langchain_parser.__class__.__name__,
                "validation_schema": self._validation_schema,
            }
        )
        return info

    def invoke(self, input_data: Any, config: Optional[Dict[str, Any]] = None) -> Any:
        """LangChain Runnable interface - synchronous invoke."""
        if isinstance(input_data, str):
            return self.parse(input_data)
        elif hasattr(input_data, "content"):
            # Handle LangChain message objects
            return self.parse(input_data.content)
        else:
            return self.parse(str(input_data))

    async def ainvoke(
        self, input_data: Any, config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """LangChain Runnable interface - asynchronous invoke."""
        return self.invoke(input_data, config)


# Factory functions for common LangChain parsers
def create_json_parser(
    name: str = "langchain_json",
    validation_schema: Optional[Dict[str, Any]] = None,
) -> LangChainWrapperParser:
    """Create a LangChain JSON parser wrapper.

    Args:
        name: Parser name
        validation_schema: Optional validation schema

    Returns:
        LangChain wrapper parser
    """
    langchain_parser = JsonOutputParser()
    return LangChainWrapperParser(name, langchain_parser, validation_schema)


def create_pydantic_parser(
    pydantic_model: BaseModel,
    name: str = "langchain_pydantic",
) -> LangChainWrapperParser:
    """Create a LangChain Pydantic parser wrapper.

    Args:
        pydantic_model: Pydantic model for parsing
        name: Parser name

    Returns:
        LangChain wrapper parser
    """
    langchain_parser = PydanticOutputParser(pydantic_object=pydantic_model)
    return LangChainWrapperParser(name, langchain_parser)
