"""Base output parser for enrichment tasks."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from langchain_core.output_parsers import BaseOutputParser as LangChainBaseOutputParser


class BaseOutputParser(ABC):
    """Base class for all output parsers.

    This class provides a unified interface for both custom parsers
    and LangChain output parsers.
    """

    def __init__(
        self, name: str, langchain_parser: Optional[LangChainBaseOutputParser] = None
    ):
        """Initialize the output parser.

        Args:
            name: Parser name for identification
            langchain_parser: Optional LangChain parser to wrap
        """
        self.name = name
        self._logger = logging.getLogger(f"enrichment.parser.{name}")
        self._langchain_parser = langchain_parser

    @abstractmethod
    def parse(self, raw_output: str) -> Dict[str, Any]:
        """Parse raw LLM output into structured data.

        Args:
            raw_output: Raw output from LLM

        Returns:
            Parsed and validated output dictionary

        Raises:
            TaskException: If parsing fails
        """
        pass

    @abstractmethod
    def validate(self, parsed_output: Dict[str, Any]) -> bool:
        """Validate parsed output structure and content.

        Args:
            parsed_output: Parsed output to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    def get_parser_info(self) -> Dict[str, Any]:
        """Get information about this parser.

        Returns:
            Parser information dictionary
        """
        info = {
            "name": self.name,
            "type": self.__class__.__name__,
        }

        if self._langchain_parser:
            info["langchain_parser"] = self._langchain_parser.__class__.__name__

        return info
