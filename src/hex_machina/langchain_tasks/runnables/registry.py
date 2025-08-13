"""Simple registry for custom LangChain runnables."""

from typing import Dict, Type

from langchain_core.runnables import Runnable


class RunnableRegistry:
    """Simple registry for custom runnables."""

    def __init__(self):
        self._runnables: Dict[str, Type[Runnable]] = {}

    def register(self, name: str, runnable_class: Type[Runnable]):
        """Register a runnable class.

        Args:
            name: Name to register the runnable under
            runnable_class: The runnable class to register
        """
        self._runnables[name] = runnable_class

    def get(self, name: str) -> Type[Runnable]:
        """Get a runnable class by name.

        Args:
            name: Name of the runnable

        Returns:
            The runnable class

        Raises:
            ValueError: If runnable not found
        """
        if name not in self._runnables:
            raise ValueError(f"Unknown runnable: {name}")
        return self._runnables[name]

    def list_available(self) -> list[str]:
        """List all available runnable names.

        Returns:
            List of available runnable names
        """
        return list(self._runnables.keys())


# Global registry instance
runnable_registry = RunnableRegistry()
