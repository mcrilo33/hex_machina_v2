"""
Configuration loader for evaluation evaluators.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from langchain_core.language_models import BaseLLM
from langchain_openai import ChatOpenAI


class EvaluationConfig:
    """Configuration manager for evaluation evaluators."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize with config file path."""
        if config_path is None:
            # Default to config/evaluation_config.yaml
            config_path = (
                Path(__file__).parent.parent.parent.parent.parent
                / "config"
                / "evaluation_config.yaml"
            )

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Evaluation config file not found: {self.config_path}"
            )

        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def get_evaluator_config(self, evaluator_name: str) -> Dict[str, Any]:
        """Get configuration for a specific evaluator."""
        evaluators = self.config.get("evaluators", {})
        if evaluator_name not in evaluators:
            raise ValueError(f"Evaluator '{evaluator_name}' not found in config")

        return evaluators[evaluator_name]

    def create_llm_from_config(self, llm_config: Dict[str, Any]) -> BaseLLM:
        """Create LLM instance from configuration."""
        provider = llm_config.get("provider", "openrouter")
        model = llm_config.get("model")
        temperature = llm_config.get("temperature", 0)
        max_tokens = llm_config.get("max_tokens", 1000)

        if provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable not set")

            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                openai_api_key=api_key,
                openai_api_base="https://openrouter.ai/api/v1",
            )

        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")

            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                openai_api_key=api_key,
            )

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def get_llm_for_evaluator(self, evaluator_name: str) -> BaseLLM:
        """Get LLM instance for a specific evaluator."""
        evaluator_config = self.get_evaluator_config(evaluator_name)
        llm_config = evaluator_config.get("llm", {})
        return self.create_llm_from_config(llm_config)

    def get_criteria_for_evaluator(
        self, evaluator_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get criteria configuration for a specific evaluator."""
        evaluator_config = self.get_evaluator_config(evaluator_name)
        return evaluator_config.get("criteria")

    def list_available_evaluators(self) -> Dict[str, Dict[str, Any]]:
        """List all available evaluators with their configurations."""
        return self.config.get("evaluators", {})
