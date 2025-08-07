"""YAML configuration system for enrichment tasks."""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field

from src.hex_machina.core import TaskException
from src.hex_machina.enrichment.tasks.base.langchain_task import LangChainTaskConfig


class TaskYAMLConfig(BaseModel):
    """YAML configuration for tasks."""

    name: str = Field(description="Task name")
    version: str = Field(default="1.0.0", description="Configuration version")
    description: Optional[str] = Field(default=None, description="Task description")
    task_type: str = Field(description="Type of task (evaluation, enrichment, etc.)")

    # LLM settings
    llm_provider: str = Field(
        description="LLM provider (openrouter, openai, anthropic)"
    )
    llm_model: str = Field(description="Model name/identifier")
    temperature: float = Field(default=0.0, description="Model temperature")
    max_tokens: Optional[int] = Field(
        default=None, description="Maximum tokens for response"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")

    # Prompt settings
    prompt_template: str = Field(description="Prompt template name or string")
    prompt_variables: Optional[Dict[str, str]] = Field(
        default=None, description="Prompt variables"
    )

    # Output settings
    output_parser: Optional[str] = Field(
        default=None, description="Output parser to use"
    )

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class TaskConfigManager:
    """Manager for task YAML configurations."""

    def __init__(self, config_dir: str = "configs/enrichment/tasks"):
        """Initialize the config manager.

        Args:
            config_dir: Directory containing task configurations
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self, task_name: str) -> TaskYAMLConfig:
        """Load task configuration from YAML file.

        Args:
            task_name: Name of the task configuration to load

        Returns:
            Task configuration

        Raises:
            TaskException: If configuration file not found or invalid
        """
        config_file = self.config_dir / f"{task_name}.yaml"

        if not config_file.exists():
            raise TaskException(f"Configuration file not found: {config_file}")

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            return TaskYAMLConfig(**config_data)

        except Exception as e:
            raise TaskException(f"Failed to load configuration {task_name}: {e}")

    def save_config(self, config: TaskYAMLConfig) -> None:
        """Save task configuration to YAML file.

        Args:
            config: Task configuration to save
        """
        config_file = self.config_dir / f"{config.name}.yaml"

        try:
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config.model_dump(), f, default_flow_style=False, indent=2)

        except Exception as e:
            raise TaskException(f"Failed to save configuration {config.name}: {e}")

    def list_configs(self) -> list[str]:
        """List available task configurations.

        Returns:
            List of available configuration names
        """
        configs = []
        for config_file in self.config_dir.glob("*.yaml"):
            configs.append(config_file.stem)
        return sorted(configs)

    def create_langchain_config(
        self, yaml_config: TaskYAMLConfig
    ) -> LangChainTaskConfig:
        """Convert YAML config to LangChain task config.

        Args:
            yaml_config: YAML configuration

        Returns:
            LangChain task configuration
        """
        return LangChainTaskConfig(
            name=yaml_config.name,
            task_type=yaml_config.task_type,
            llm_provider=yaml_config.llm_provider,
            llm_model=yaml_config.llm_model,
            temperature=yaml_config.temperature,
            max_tokens=yaml_config.max_tokens,
            timeout=yaml_config.timeout,
            prompt_template=yaml_config.prompt_template,
            prompt_variables=yaml_config.prompt_variables,
            output_parser=yaml_config.output_parser,
        )


# Global config manager instance
task_config_manager = TaskConfigManager()
