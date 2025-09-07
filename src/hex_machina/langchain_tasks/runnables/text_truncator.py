"""
Text truncator runnable for reducing article content size.

This runnable uses TransformChain to truncate long text content while preserving
the beginning and ending portions of articles.
"""

from typing import Any, Dict, Optional

from langchain.chains import TransformChain
from langchain_core.runnables import Runnable


class TextTruncatorRunnable(Runnable):
    """
    Custom runnable that truncates long text content using TransformChain.

    This runnable is designed to reduce the size of article content while preserving
    the most important parts (beginning and ending) for analysis.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """Initialize the text truncator.

        Args:
            config: Configuration dictionary with truncation parameters
            **kwargs: Additional keyword arguments (for registry compatibility)
        """
        # Handle both config dict and keyword arguments
        if config is None:
            config = {}

        # Merge config with kwargs for registry compatibility
        config.update(kwargs)

        self.config = config
        self.truncate_length = self.config.get("truncate_length", 500)

        # Create the TransformChain with our truncation function
        self.transform_chain = TransformChain(
            input_variables=["text_content", "title"],
            output_variables=["text_content", "title"],
            transform=self._truncate_text,
        )

    def _truncate_text(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Truncate the text content while preserving beginning and ending.

        Args:
            inputs: Dictionary containing 'text_content' and 'title'

        Returns:
            Dictionary with truncated 'text_content' and original 'title'
        """
        text_content = inputs.get("text_content", "")
        title = inputs.get("title", "")

        if not text_content or len(text_content) <= (self.truncate_length * 2):
            # No truncation needed
            return {"text_content": text_content, "title": title}

        # Extract beginning and ending portions
        beginning = text_content[: self.truncate_length]
        ending = text_content[-self.truncate_length :]

        # Create truncated content with separator
        truncated_content = f"{beginning}\n\n[...]\n\n{ending}"

        return {"text_content": truncated_content, "title": title}

    def invoke(
        self, input_data: Any, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process the input data using the TransformChain.

        Args:
            input_data: Input data containing text_content and title
            config: Runtime configuration (optional)

        Returns:
            Dictionary containing truncated text_content and title
        """
        # Ensure input_data is a dictionary
        if not isinstance(input_data, dict):
            raise ValueError(
                "Input data must be a dictionary with 'text_content' and 'title' keys"
            )

        # Use the TransformChain to process the data
        result = self.transform_chain.invoke(input_data)

        # Add metadata about the truncation
        original_length = len(input_data.get("text_content", ""))
        truncated_length = len(result.get("text_content", ""))

        result["truncation_metadata"] = {
            "original_length": original_length,
            "truncated_length": truncated_length,
            "was_truncated": original_length > truncated_length,
            "truncation_config": {
                "truncate_length": self.truncate_length,
            },
        }

        return result

    def get_input_schema(self):
        """Get the input schema for this runnable."""
        from pydantic import BaseModel

        class InputSchema(BaseModel):
            text_content: str = "The text content to truncate"
            title: str = "The article title"

        return InputSchema

    def get_output_schema(self):
        """Get the output schema for this runnable."""
        from pydantic import BaseModel

        class OutputSchema(BaseModel):
            text_content: str = "The truncated text content"
            title: str = "The article title"
            truncation_metadata: Dict[str, Any] = (
                "Metadata about the truncation process"
            )

        return OutputSchema
