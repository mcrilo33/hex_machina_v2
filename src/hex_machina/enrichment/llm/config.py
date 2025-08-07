"""LLM configuration for the enrichment evaluation system."""

import os
from typing import Optional

from langchain_openai import ChatOpenAI


class LLMConfig:
    """Configuration for LLM models used in evaluation."""

    # OpenRouter configuration
    OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

    # Default model settings
    DEFAULT_MODEL = "openai/gpt-3.5-turbo"
    DEFAULT_TEMPERATURE = 0  # Low temperature for consistent evaluation

    # Available models through OpenRouter
    AVAILABLE_MODELS = {
        "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
        "gpt-4": "openai/gpt-4",
        "gpt-4-turbo": "openai/gpt-4-turbo-preview",
        "claude-3-haiku": "anthropic/claude-3-haiku-20240307",
        "claude-3-sonnet": "anthropic/claude-3-sonnet-20240229",
        "claude-3-opus": "anthropic/claude-3-opus-20240229",
        "gemini-pro": "google/gemini-pro",
        "llama-2-70b": "meta-llama/llama-2-70b-chat",
        "mistral-7b": "mistralai/mistral-7b-instruct",
    }

    @classmethod
    def create_llm(
        cls,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        api_key: Optional[str] = None,
    ) -> ChatOpenAI:
        """Create an LLM instance with OpenRouter configuration.

        Args:
            model: Model identifier or alias. If None, uses default.
            temperature: Model temperature. If None, uses default.
            api_key: OpenRouter API key. If None, uses environment variable.

        Returns:
            ChatOpenAI: Configured LLM instance

        Raises:
            ValueError: If API key is not configured.
        """
        # Use defaults if not provided
        model = model or cls.DEFAULT_MODEL
        temperature = (
            temperature if temperature is not None else cls.DEFAULT_TEMPERATURE
        )
        api_key = api_key or cls.OPENROUTER_API_KEY

        if not api_key:
            raise ValueError(
                "OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable."
            )

        # Resolve model alias if provided
        if model in cls.AVAILABLE_MODELS:
            model = cls.AVAILABLE_MODELS[model]

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_base=cls.OPENROUTER_API_BASE,
            openai_api_key=api_key,
        )

    @classmethod
    def list_available_models(cls) -> dict[str, str]:
        """Get list of available models with their OpenRouter identifiers.

        Returns:
            dict: Mapping of model aliases to OpenRouter identifiers.
        """
        return cls.AVAILABLE_MODELS.copy()

    @classmethod
    def validate_api_key(cls) -> bool:
        """Validate that OpenRouter API key is configured.

        Returns:
            bool: True if API key is configured, False otherwise.
        """
        return bool(cls.OPENROUTER_API_KEY)


def create_evaluation_llm(
    model: str = "gpt-3.5-turbo", temperature: float = 0
) -> ChatOpenAI:
    """Create an LLM instance optimized for content evaluation.

    Args:
        model: Model to use (can be alias or full identifier).
        temperature: Model temperature (0 for consistent results).

    Returns:
        ChatOpenAI: Configured LLM for evaluation.
    """
    return LLMConfig.create_llm(model=model, temperature=temperature)
