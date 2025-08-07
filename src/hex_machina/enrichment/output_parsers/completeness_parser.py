"""Content completeness output parser using LangChain."""

from typing import Any, Dict, List

from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from src.hex_machina.enrichment.models import CompletenessIssue

from .langchain_wrapper import LangChainWrapperParser


class CompletenessOutput(BaseModel):
    """Pydantic model for content completeness output."""

    is_complete: bool = Field(description="Whether the article content is complete")
    detected_issues: List[str] = Field(
        default_factory=list, description="List of detected completeness issues"
    )

    @classmethod
    def validate_detected_issues(cls, value: List[str]) -> List[str]:
        """Validate that detected issues are valid enum values."""
        valid_issues = {issue.value for issue in CompletenessIssue}
        for issue in value:
            if issue not in valid_issues:
                raise ValueError(
                    f"Invalid completeness issue: {issue}. Valid issues: {valid_issues}"
                )
        return value


class CompletenessOutputParser(LangChainWrapperParser, Runnable):
    """Parser for content completeness evaluation outputs using LangChain."""

    def __init__(self, name: str = "completeness_parser"):
        """Initialize completeness parser.

        Args:
            name: Parser name
        """
        # Create Pydantic model for validation
        completeness_model = CompletenessOutput

        # Create LangChain PydanticOutputParser
        from langchain_core.output_parsers import PydanticOutputParser

        langchain_parser = PydanticOutputParser(pydantic_object=completeness_model)

        # Initialize wrapper
        super().__init__(name, langchain_parser)

    def get_parser_info(self) -> Dict[str, Any]:
        """Get parser information with completeness-specific details."""
        info = super().get_parser_info()
        info.update(
            {
                "valid_issues": [issue.value for issue in CompletenessIssue],
                "description": "Parser for content completeness evaluation outputs using LangChain PydanticOutputParser",
            }
        )
        return info
