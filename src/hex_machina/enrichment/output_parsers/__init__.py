"""Output parsers for enrichment tasks."""

from .base import BaseOutputParser
from .completeness_parser import CompletenessOutputParser
from .json_parser import JSONOutputParser
from .langchain_wrapper import (
    LangChainWrapperParser,
    create_json_parser,
    create_pydantic_parser,
)
from .registry import OutputParserRegistry, parser_registry

# Register built-in parsers
parser_registry.register(JSONOutputParser)
parser_registry.register(CompletenessOutputParser)
parser_registry.register(LangChainWrapperParser)

__all__ = [
    "BaseOutputParser",
    "JSONOutputParser",
    "CompletenessOutputParser",
    "LangChainWrapperParser",
    "create_json_parser",
    "create_pydantic_parser",
    "OutputParserRegistry",
    "parser_registry",
]
