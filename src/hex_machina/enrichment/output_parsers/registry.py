"""Output parser registry."""

import logging
from typing import Dict, List, Optional, Type

from .base import BaseOutputParser


class OutputParserRegistry:
    """Registry for output parsers."""

    def __init__(self):
        """Initialize the parser registry."""
        self._parsers: Dict[str, Type[BaseOutputParser]] = {}
        self._logger = logging.getLogger("enrichment.parser.registry")

    def register(self, parser_class: Type[BaseOutputParser]) -> None:
        """Register a parser class.

        Args:
            parser_class: The parser class to register
        """
        parser_name = parser_class.__name__
        self._parsers[parser_name] = parser_class
        self._logger.info(f"Registered parser: {parser_name}")

    def get_parser(self, parser_name: str) -> Optional[Type[BaseOutputParser]]:
        """Get a parser class by name.

        Args:
            parser_name: Name of the parser to retrieve

        Returns:
            The parser class, or None if not found
        """
        return self._parsers.get(parser_name)

    def create_parser(self, parser_name: str, **kwargs) -> Optional[BaseOutputParser]:
        """Create a parser instance by name.

        Args:
            parser_name: Name of the parser to create
            **kwargs: Arguments to pass to the parser constructor

        Returns:
            Parser instance, or None if parser not found
        """
        parser_class = self.get_parser(parser_name)
        if parser_class is None:
            self._logger.error(f"Parser not found: {parser_name}")
            return None

        try:
            return parser_class(**kwargs)
        except Exception as e:
            self._logger.error(f"Failed to create parser {parser_name}: {e}")
            return None

    def list_parsers(self) -> List[str]:
        """List all registered parser names.

        Returns:
            List of registered parser names
        """
        return list(self._parsers.keys())

    def discover_parsers(self, module_path: str) -> None:
        """Discover and register parsers from a module.

        Args:
            module_path: Path to the module containing parsers
        """
        try:
            import importlib

            module = importlib.import_module(module_path)

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseOutputParser)
                    and attr != BaseOutputParser
                ):
                    self.register(attr)

        except Exception as e:
            self._logger.error(f"Failed to discover parsers from {module_path}: {e}")


# Global parser registry instance
parser_registry = OutputParserRegistry()
