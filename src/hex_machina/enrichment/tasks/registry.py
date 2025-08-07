"""Task registry for discovering and managing enrichment tasks."""

import logging
from typing import Dict, Optional, Type

from src.hex_machina.enrichment.core import EnrichmentTask
from src.hex_machina.enrichment.tasks.base.langchain_task import LangChainTask
from src.hex_machina.enrichment.tasks.content_completeness_langchain import (
    ContentCompletenessLangChainTask,
)


class TaskRegistry:
    """Registry for enrichment tasks."""

    def __init__(self):
        """Initialize the task registry."""
        self._tasks: Dict[str, Type[EnrichmentTask]] = {}
        self._logger = logging.getLogger("enrichment.task.registry")

        # Register built-in tasks
        self._register_builtin_tasks()

    def _register_builtin_tasks(self) -> None:
        """Register built-in tasks."""
        self.register(ContentCompletenessLangChainTask)

    def register(self, task_class: Type[EnrichmentTask]) -> None:
        """Register a task class.

        Args:
            task_class: The task class to register
        """
        task_name = task_class.__name__
        self._tasks[task_name] = task_class
        self._logger.info(f"Registered task: {task_name}")

    def get_task(self, task_name: str) -> Optional[Type[EnrichmentTask]]:
        """Get a task class by name.

        Args:
            task_name: Name of the task to retrieve

        Returns:
            The task class, or None if not found
        """
        return self._tasks.get(task_name)

    def create_task(self, task_name: str, config) -> Optional[EnrichmentTask]:
        """Create a task instance by name.

        Args:
            task_name: Name of the task to create
            config: Task configuration

        Returns:
            Task instance, or None if task not found
        """
        task_class = self.get_task(task_name)
        if not task_class:
            self._logger.error(f"Task not found: {task_name}")
            return None

        try:
            return task_class(config)
        except Exception as e:
            self._logger.error(f"Failed to create task {task_name}: {e}")
            return None

    def list_tasks(self) -> list[str]:
        """List all registered task names.

        Returns:
            List of registered task names
        """
        return list(self._tasks.keys())

    def get_task_info(self, task_name: str) -> Optional[Dict]:
        """Get information about a task.

        Args:
            task_name: Name of the task

        Returns:
            Task information dictionary, or None if not found
        """
        task_class = self.get_task(task_name)
        if not task_class:
            return None

        return {
            "name": task_name,
            "class": task_class.__name__,
            "module": task_class.__module__,
            "docstring": task_class.__doc__,
            "is_langchain": issubclass(task_class, LangChainTask),
        }


# Global task registry instance
task_registry = TaskRegistry()
