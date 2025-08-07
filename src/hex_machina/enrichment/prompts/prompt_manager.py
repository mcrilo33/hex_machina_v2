"""Prompt manager for enrichment tasks."""

import logging
from typing import Any, Dict, Optional

from src.hex_machina.enrichment.evaluation.langchain.prompts.evaluation_prompts import (
    ARTICLE_COMPLETENESS_EVALUATION_PROMPT,
)


class PromptManager:
    """Simple prompt manager for enrichment tasks."""

    def __init__(self):
        """Initialize the prompt manager."""
        self._logger = logging.getLogger("enrichment.prompts")
        self._prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, Any]:
        """Load available prompts.

        Returns:
            Dictionary of available prompts
        """
        return {
            "evaluation/completeness": ARTICLE_COMPLETENESS_EVALUATION_PROMPT,
            # Add more prompts here as needed
        }

    def get_prompt(self, prompt_name: str) -> Optional[Any]:
        """Get a prompt by name.

        Args:
            prompt_name: Name of the prompt to retrieve

        Returns:
            Prompt template or None if not found
        """
        return self._prompts.get(prompt_name)

    def format_prompt(self, prompt_name: str, **kwargs) -> str:
        """Format a prompt with the given variables.

        Args:
            prompt_name: Name of the prompt to format
            **kwargs: Variables to substitute in the prompt

        Returns:
            Formatted prompt string

        Raises:
            ValueError: If prompt not found or formatting fails
        """
        prompt = self.get_prompt(prompt_name)
        if not prompt:
            raise ValueError(f"Prompt not found: {prompt_name}")

        try:
            if hasattr(prompt, "format"):
                # Handle string templates
                return prompt.format(**kwargs)
            elif hasattr(prompt, "format_prompt"):
                # Handle LangChain prompt templates
                return prompt.format_prompt(**kwargs).to_string()
            else:
                raise ValueError(f"Unsupported prompt type: {type(prompt)}")

        except Exception as e:
            self._logger.error(f"Failed to format prompt {prompt_name}: {e}")
            raise ValueError(f"Prompt formatting failed: {e}")

    def list_prompts(self) -> list:
        """List available prompt names.

        Returns:
            List of available prompt names
        """
        return list(self._prompts.keys())


# Global prompt manager instance
prompt_manager = PromptManager()
