"""Core base classes for the Hex Machina project."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BaseModule:
    """Base class for all modules in the project."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.created_at = datetime.utcnow()

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)


class BaseConfig(BaseModel):
    """Base configuration class for all modules."""

    name: str = Field(..., description="Configuration name")
    description: Optional[str] = Field(None, description="Configuration description")
    version: str = Field("1.0.0", description="Configuration version")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BaseStorage(ABC):
    """Base storage interface for all modules."""

    @abstractmethod
    async def store(self, data: Dict[str, Any]) -> str:
        """Store data and return identifier."""
        pass

    @abstractmethod
    async def retrieve(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Retrieve data by identifier."""
        pass

    @abstractmethod
    async def update(self, identifier: str, data: Dict[str, Any]) -> bool:
        """Update data by identifier."""
        pass

    @abstractmethod
    async def delete(self, identifier: str) -> bool:
        """Delete data by identifier."""
        pass


class BaseTask(ABC):
    """Base task interface for all tasks."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        self.task_type = config.get("task_type", "unknown")

    @abstractmethod
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the task."""
        pass

    @abstractmethod
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate task inputs."""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Get task metadata."""
        return {
            "name": self.name,
            "task_type": self.task_type,
            "config": self.config,
            "created_at": datetime.utcnow().isoformat(),
        }


class BaseWorkflow(ABC):
    """Base workflow interface for all workflows."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        self.workflow_type = config.get("workflow_type", "sequential")

    @abstractmethod
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the workflow."""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate workflow configuration."""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Get workflow metadata."""
        return {
            "name": self.name,
            "workflow_type": self.workflow_type,
            "config": self.config,
            "created_at": datetime.utcnow().isoformat(),
        }


class BaseEvaluator(ABC):
    """Base evaluator interface for all evaluators."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        self.evaluator_type = config.get("evaluator_type", "unknown")

    @abstractmethod
    async def evaluate(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate the inputs."""
        pass

    @abstractmethod
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate evaluator inputs."""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Get evaluator metadata."""
        return {
            "name": self.name,
            "evaluator_type": self.evaluator_type,
            "config": self.config,
            "created_at": datetime.utcnow().isoformat(),
        }


class TaskInput(BaseModel):
    """Input model for tasks."""

    data: Dict[str, Any] = Field(..., description="Task input data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Task input metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskOutput(BaseModel):
    """Output model for tasks."""

    result: Dict[str, Any] = Field(..., description="Task output result")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Task output metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    execution_time_ms: Optional[float] = Field(
        None, description="Task execution time in milliseconds"
    )


class WorkflowResult(BaseModel):
    """Result model for workflows."""

    workflow_name: str = Field(..., description="Workflow name")
    success: bool = Field(..., description="Whether workflow succeeded")
    result: Dict[str, Any] = Field(..., description="Workflow result")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Workflow metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    execution_time_ms: Optional[float] = Field(
        None, description="Workflow execution time in milliseconds"
    )


class EvaluationResult(BaseModel):
    """Result model for evaluations."""

    evaluator_name: str = Field(..., description="Evaluator name")
    score: Optional[float] = Field(None, description="Evaluation score")
    metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Evaluation metrics"
    )
    feedback: Optional[str] = Field(None, description="Evaluation feedback")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Evaluation metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
