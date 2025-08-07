"""Task registry for enrichment tasks."""

import logging
from typing import Dict, List, Optional, Type

from .base import EnrichmentTask


class TaskRegistry:
    """Registry for enrichment tasks."""

    def __init__(self):
        self._tasks: Dict[str, Type[EnrichmentTask]] = {}
        self._logger = logging.getLogger("enrichment.registry")

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

    def list_tasks(self) -> List[str]:
        """List all registered task names.

        Returns:
            List of registered task names
        """
        return list(self._tasks.keys())

    def create_task(self, task_name: str, **kwargs) -> Optional[EnrichmentTask]:
        """Create a task instance by name.

        Args:
            task_name: Name of the task to create
            **kwargs: Arguments to pass to the task constructor

        Returns:
            Task instance, or None if task not found
        """
        task_class = self.get_task(task_name)
        if task_class is None:
            self._logger.error(f"Task not found: {task_name}")
            return None

        try:
            return task_class(**kwargs)
        except Exception as e:
            self._logger.error(f"Failed to create task {task_name}: {e}")
            return None

    def discover_tasks(self, module_path: str) -> None:
        """Discover and register tasks from a module.

        Args:
            module_path: Path to the module containing tasks
        """
        try:
            import importlib

            module = importlib.import_module(module_path)

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, EnrichmentTask)
                    and attr != EnrichmentTask
                ):
                    self.register(attr)

        except Exception as e:
            self._logger.error(f"Failed to discover tasks from {module_path}: {e}")


# Global task registry instance
task_registry = TaskRegistry()
