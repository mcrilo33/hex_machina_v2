"""Base classes for enrichment functionality."""

import logging
from abc import abstractmethod
from typing import List, Optional

from pydantic import Field

from src.hex_machina.core import (
    BaseConfig,
    BaseEvaluator,
    BaseTask,
    BaseWorkflow,
    EvaluationResult,
    TaskInput,
    TaskOutput,
    WorkflowResult,
)


class EnrichmentConfig(BaseConfig):
    """Configuration for enrichment components."""

    task_type: str = Field(description="Type of enrichment task")
    llm_provider: str = Field(
        description="LLM provider (openai, anthropic, openrouter)"
    )
    llm_model: str = Field(description="Model name/identifier")
    temperature: float = Field(default=0.0, description="Model temperature")
    max_tokens: Optional[int] = Field(
        default=None, description="Maximum tokens for response"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")


class EnrichmentTask(BaseTask):
    """Base class for enrichment tasks."""

    def __init__(self, name: str, config: Optional[EnrichmentConfig] = None):
        super().__init__(name, config)
        self._logger = logging.getLogger(f"enrichment.task.{name}")

    def initialize(self) -> None:
        """Initialize the enrichment task."""
        self._logger.info(f"Initializing enrichment task: {self.name}")

    def cleanup(self) -> None:
        """Clean up task resources."""
        self._logger.info(f"Cleaning up enrichment task: {self.name}")

    @abstractmethod
    async def execute(self, input_data: TaskInput) -> TaskOutput:
        """Execute the enrichment task."""
        pass

    @abstractmethod
    def validate_input(self, input_data: TaskInput) -> bool:
        """Validate the input data for this task."""
        pass


class EnrichmentWorkflow(BaseWorkflow):
    """Base class for enrichment workflows."""

    def __init__(self, name: str, config: Optional[EnrichmentConfig] = None):
        super().__init__(name, config)
        self._logger = logging.getLogger(f"enrichment.workflow.{name}")

    def initialize(self) -> None:
        """Initialize the enrichment workflow."""
        self._logger.info(f"Initializing enrichment workflow: {self.name}")
        for task in self.tasks:
            task.initialize()

    def cleanup(self) -> None:
        """Clean up workflow resources."""
        self._logger.info(f"Cleaning up enrichment workflow: {self.name}")
        for task in self.tasks:
            task.cleanup()

    @abstractmethod
    async def execute(self, input_data: TaskInput) -> WorkflowResult:
        """Execute the enrichment workflow."""
        pass


class EnrichmentEvaluator(BaseEvaluator):
    """Base class for enrichment evaluators."""

    def __init__(self, name: str, config: Optional[EnrichmentConfig] = None):
        super().__init__(name, config)
        self._logger = logging.getLogger(f"enrichment.evaluator.{name}")

    def initialize(self) -> None:
        """Initialize the enrichment evaluator."""
        self._logger.info(f"Initializing enrichment evaluator: {self.name}")

    def cleanup(self) -> None:
        """Clean up evaluator resources."""
        self._logger.info(f"Cleaning up enrichment evaluator: {self.name}")

    @abstractmethod
    async def evaluate(self, task_output: TaskOutput) -> EvaluationResult:
        """Evaluate the output of a task."""
        pass

    @abstractmethod
    def get_metrics(self) -> List[str]:
        """Get the list of metrics this evaluator produces."""
        pass
