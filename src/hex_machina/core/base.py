"""Base classes and data models for Hex Machina v2."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

# =============================================================================
# Data Models for Task/Workflow Communication
# =============================================================================


class TaskInput(BaseModel):
    """Input data for a task execution."""

    task_id: str = Field(description="Unique identifier for the task")
    task_name: str = Field(description="Name of the task to execute")
    input_data: Dict[str, Any] = Field(description="Input data for the task")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )

    # Database integration fields
    article_id: Optional[int] = Field(
        default=None, description="Database article ID if input is from DB"
    )
    article_url: Optional[str] = Field(
        default=None, description="Article URL for identification"
    )
    workflow_operation_id: Optional[str] = Field(
        default=None, description="Workflow context identifier"
    )
    save_to_db: bool = Field(
        default=True, description="Whether to save enrichment to database"
    )


class TaskOutput(BaseModel):
    """Output data from a task execution."""

    task_id: str = Field(description="Unique identifier for the task")
    output_data: Dict[str, Any] = Field(description="Output data from the task")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    execution_time: float = Field(description="Task execution time in seconds")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if task failed"
    )


class WorkflowResult(BaseModel):
    """Result from a workflow execution."""

    workflow_id: str = Field(description="Unique identifier for the workflow")
    task_results: List[TaskOutput] = Field(
        description="Results from all tasks in the workflow"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    total_execution_time: float = Field(
        description="Total workflow execution time in seconds"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    status: str = Field(description="Workflow status: 'completed', 'failed', 'partial'")


class EvaluationResult(BaseModel):
    """Result from an evaluation execution."""

    evaluation_id: str = Field(description="Unique identifier for the evaluation")
    task_id: str = Field(description="ID of the task being evaluated")
    metrics: Dict[str, Union[float, int, str, bool]] = Field(
        description="Evaluation metrics"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )


# =============================================================================
# Base Classes for Core Components
# =============================================================================


class BaseConfig(BaseModel):
    """Base configuration class for all components."""

    name: str = Field(description="Configuration name")
    version: str = Field(default="1.0.0", description="Configuration version")
    description: Optional[str] = Field(
        default=None, description="Configuration description"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class BaseModule(ABC):
    """Base class for all modules in Hex Machina."""

    def __init__(self, name: str, config: Optional[BaseConfig] = None):
        self.name = name
        self.config = config
        self._logger = None  # Will be set by subclasses

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the module."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up module resources."""
        pass


class BaseTask(BaseModule):
    """Base class for all tasks in the enrichment system."""

    def __init__(self, name: str, config: Optional[BaseConfig] = None):
        super().__init__(name, config)
        self.task_id = str(uuid4())

    @abstractmethod
    async def execute(self, input_data: TaskInput) -> TaskOutput:
        """Execute the task with the given input data."""
        pass

    @abstractmethod
    def validate_input(self, input_data: TaskInput) -> bool:
        """Validate the input data for this task."""
        pass

    def get_task_info(self) -> Dict[str, Any]:
        """Get information about this task."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "config": self.config.model_dump() if self.config else None,
        }


class BaseWorkflow(BaseModule):
    """Base class for all workflows in the enrichment system."""

    def __init__(self, name: str, config: Optional[BaseConfig] = None):
        super().__init__(name, config)
        self.workflow_id = str(uuid4())
        self.tasks: List[BaseTask] = []

    @abstractmethod
    async def execute(self, input_data: TaskInput) -> WorkflowResult:
        """Execute the workflow with the given input data."""
        pass

    def add_task(self, task: BaseTask) -> None:
        """Add a task to this workflow."""
        self.tasks.append(task)

    def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about this workflow."""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "config": self.config.model_dump() if self.config else None,
            "task_count": len(self.tasks),
        }


class BaseEvaluator(BaseModule):
    """Base class for all evaluators in the enrichment system."""

    def __init__(self, name: str, config: Optional[BaseConfig] = None):
        super().__init__(name, config)
        self.evaluator_id = str(uuid4())

    @abstractmethod
    async def evaluate(self, task_output: TaskOutput) -> EvaluationResult:
        """Evaluate the output of a task."""
        pass

    @abstractmethod
    def get_metrics(self) -> List[str]:
        """Get the list of metrics this evaluator produces."""
        pass

    def get_evaluator_info(self) -> Dict[str, Any]:
        """Get information about this evaluator."""
        return {
            "evaluator_id": self.evaluator_id,
            "name": self.name,
            "config": self.config.model_dump() if self.config else None,
            "metrics": self.get_metrics(),
        }
