"""
Step dataset manager for LangChain tasks.

This module manages the creation and population of step-range datasets
during task execution.
"""

import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from .generator import DatasetGenerator


class StepDatasetManager:
    """
    Manager for step-range datasets during task execution.

    This class coordinates:
    - Run_id tracking across steps
    - Integration with TaskBuilder for step-range dataset creation
    """

    def __init__(
        self,
        generator: Optional[DatasetGenerator] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the step dataset manager.

        Args:
            generator: Dataset generator instance
            config: Task-level dataset configuration
        """
        self.generator = generator or DatasetGenerator(config=config)
        self.config = config or {}
        self._logger = logging.getLogger("langchain_tasks.datasets.step_manager")

        # Track current task execution
        self._current_run_id: Optional[str] = None
        self._current_task_name: Optional[str] = None

        self._logger.info("StepDatasetManager initialized")

    def start_task_execution(self, task_name: str) -> str:
        """Start tracking a new task execution.

        Args:
            task_name: Name of the task being executed

        Returns:
            Unique run_id for this task execution
        """
        self._current_run_id = str(uuid4())
        self._current_task_name = task_name

        self._logger.info(
            f"Started task execution: {task_name} (run_id: {self._current_run_id})"
        )
        return self._current_run_id

    def end_task_execution(self) -> Dict[str, Any]:
        """End the current task execution and return summary.

        Returns:
            Dictionary with execution summary
        """
        if not self._current_run_id or not self._current_task_name:
            return {"error": "No active task execution"}

        summary = {
            "task_name": self._current_task_name,
            "run_id": self._current_run_id,
            "status": "completed",
        }

        # Clear current execution state
        self._current_run_id = None
        self._current_task_name = None

        self._logger.info(f"Task execution ended: {summary['task_name']}")
        return summary

    def get_current_run_id(self) -> Optional[str]:
        """Get the current task execution run ID.

        Returns:
            Current run ID if a task is executing, None otherwise
        """
        return self._current_run_id

    def get_current_task_name(self) -> Optional[str]:
        """Get the current task name.

        Returns:
            Current task name if a task is executing, None otherwise
        """
        return self._current_task_name

    def is_task_executing(self) -> bool:
        """Check if a task is currently executing.

        Returns:
            True if a task is executing, False otherwise
        """
        return self._current_run_id is not None and self._current_task_name is not None
