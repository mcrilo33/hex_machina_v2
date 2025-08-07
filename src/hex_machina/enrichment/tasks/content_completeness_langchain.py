"""LangChain-aligned content completeness evaluation task."""

from typing import Optional

from src.hex_machina.core import TaskInput
from src.hex_machina.enrichment.tasks.base.langchain_task import (
    LangChainTask,
    LangChainTaskConfig,
)


class ContentCompletenessLangChainTask(LangChainTask):
    """LangChain-aligned task for evaluating content completeness of articles."""

    def __init__(self, config: LangChainTaskConfig):
        """Initialize the ContentCompleteness LangChain task.

        Args:
            config: LangChain task configuration
        """
        super().__init__("content_completeness_langchain", config)

    def validate_input(self, input_data: TaskInput) -> bool:
        """Validate the input data for this task.

        Args:
            input_data: Task input data

        Returns:
            True if input is valid, False otherwise
        """
        try:
            # Check if required fields are present
            if "title" not in input_data.input_data:
                self._logger.error("Missing 'title' in input data")
                return False

            if "content" not in input_data.input_data:
                self._logger.error("Missing 'content' in input data")
                return False

            # Validate that content is not empty
            content = input_data.input_data["content"]
            if not content or not content.strip():
                self._logger.error("Content is empty")
                return False

            return True

        except Exception as e:
            self._logger.error(f"Error validating input: {e}")
            return False

    def get_default_parser_name(self) -> Optional[str]:
        """Get the default output parser name for this task.

        Returns:
            Default parser name
        """
        return "CompletenessOutputParser"
