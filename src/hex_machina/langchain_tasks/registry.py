"""
Runnable Registry for LangChain tasks.

This registry follows LangChain's philosophy where everything is a runnable.
It provides class registration for custom runnables and auto-discovers
LangChain built-in runnables.
"""

import importlib
import inspect
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Type, Union

from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field


class RegistryConfig(BaseModel):
    """Configuration for the registry."""

    auto_discover_builtins: bool = Field(
        default=True, description="Automatically discover common LangChain runnables"
    )
    auto_discover_custom: bool = Field(
        default=True,
        description="Automatically discover custom runnables from runnables module",
    )
    builtin_modules: list[str] = Field(
        default=[
            "langchain_openai",
            "langchain_anthropic",
            "langchain_core.prompts",
            "langchain_core.output_parsers",
        ],
        description="Modules to scan for built-in runnables",
    )
    custom_runnables: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom runnable mappings (name -> import_path)",
    )


class RunnableRegistry(Runnable):
    """
    Registry for discovering and instantiating runnables.

    This follows LangChain's philosophy where everything is a runnable.
    Can be used in LCEL chains for dynamic runnable selection.

    Features:
    - Class registration for custom runnables
    - Auto-discovery of LangChain built-in runnables
    - Auto-discovery of custom runnables from runnables module
    - LCEL compatibility (implements Runnable interface)
    """

    def __init__(self, config: Optional[RegistryConfig] = None):
        """Initialize the registry.

        Args:
            config: Registry configuration
        """
        self.config = config or RegistryConfig()
        self._logger = logging.getLogger("langchain_tasks.registry")

        # Registry storage
        self._custom_registry: Dict[str, Type[Runnable]] = {}
        self._builtin_registry: Dict[str, Type[Runnable]] = {}

        # Auto-discover built-ins if enabled
        if self.config.auto_discover_builtins:
            self._auto_discover_builtins()

        # Auto-discover custom runnables if enabled
        if self.config.auto_discover_custom:
            self._auto_discover_custom_runnables()

        # Register custom runnables from config
        self._register_custom_runnables()

        self._logger.info(
            f"RunnableRegistry initialized with {len(self._custom_registry)} custom and {len(self._builtin_registry)} built-in runnables"
        )

    def _auto_discover_builtins(self) -> None:
        """Auto-discover common LangChain runnables."""
        self._logger.info("Auto-discovering LangChain built-in runnables...")

        # Common runnable classes to discover
        builtin_classes = {
            # LLMs
            "ChatOpenAI": "langchain_openai",
            "ChatAnthropic": "langchain_anthropic",
            "ChatGoogleGenerativeAI": "langchain_google_genai",
            # Prompts
            "PromptTemplate": "langchain_core.prompts",
            "ChatPromptTemplate": "langchain_core.prompts",
            # Output Parsers
            "StringOutputParser": "langchain_core.output_parsers",
            "JsonOutputParser": "langchain_core.output_parsers",
            "PydanticOutputParser": "langchain_core.output_parsers",
            # Tools and Retrievers
            "Tool": "langchain_core.tools",
            "Retriever": "langchain_core.retrievers",
        }

        for class_name, module_path in builtin_classes.items():
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    runnable_class = getattr(module, class_name)
                    if isinstance(runnable_class, type) and issubclass(
                        runnable_class, Runnable
                    ):
                        self._builtin_registry[class_name] = runnable_class
                        self._logger.debug(
                            f"Discovered built-in runnable: {class_name} from {module_path}"
                        )
            except ImportError:
                # Module not available, skip
                pass
            except Exception as e:
                self._logger.debug(f"Failed to discover {class_name}: {e}")

    def _auto_discover_custom_runnables(self) -> None:
        """Auto-discover custom runnables from the runnables module and custom_runnables package."""
        self._logger.info("Auto-discovering custom runnables...")

        # Discover from runnables module (existing functionality)
        try:
            # Import the runnables module to trigger registration
            from . import runnables

            # Get the runnable registry from the runnables module
            if hasattr(runnables, "runnable_registry"):
                custom_registry = runnables.runnable_registry

                # Get all registered runnables
                for name in custom_registry.list_available():
                    try:
                        runnable_class = custom_registry.get(name)
                        if isinstance(runnable_class, type) and issubclass(
                            runnable_class, Runnable
                        ):
                            self._custom_registry[name] = runnable_class
                            self._logger.debug(f"Discovered custom runnable: {name}")
                        else:
                            self._logger.warning(
                                f"Invalid custom runnable class: {name} -> {type(runnable_class)}"
                            )
                    except Exception as e:
                        self._logger.warning(
                            f"Failed to load custom runnable {name}: {e}"
                        )

        except ImportError as e:
            self._logger.debug(f"Could not import runnables module: {e}")
        except Exception as e:
            self._logger.debug(
                f"Failed to auto-discover custom runnables from runnables module: {e}"
            )

        # Discover from custom_runnables package (new functionality)
        try:
            # Import the custom_runnables package
            custom_package = importlib.import_module(
                "src.hex_machina.langchain_tasks.custom_runnables"
            )

            # Get the package path
            package_path = Path(custom_package.__file__).parent

            # Discover Python files in the package
            for py_file in package_path.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                # Import the module
                module_name = (
                    f"src.hex_machina.langchain_tasks.custom_runnables.{py_file.stem}"
                )
                try:
                    module = importlib.import_module(module_name)

                    # Look for runnable classes in the module
                    for name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, Runnable)
                            and obj != Runnable
                        ):
                            # Register the custom runnable
                            self._custom_registry[name] = obj
                            self._logger.info(
                                f"Auto-discovered custom runnable: {name} from {module_name}"
                            )

                except Exception as e:
                    self._logger.warning(
                        f"Failed to import custom runnable module {module_name}: {e}"
                    )

        except Exception as e:
            self._logger.debug(
                f"Failed to auto-discover custom runnables from custom_runnables package: {e}"
            )

    def _register_custom_runnables(self) -> None:
        """Register custom runnables from configuration."""
        for name, import_path in self.config.custom_runnables.items():
            try:
                module_path, class_name = import_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                runnable_class = getattr(module, class_name)

                if isinstance(runnable_class, type) and issubclass(
                    runnable_class, Runnable
                ):
                    self.register(name, runnable_class)
                    self._logger.info(
                        f"Registered custom runnable from config: {name} -> {import_path}"
                    )
                else:
                    self._logger.warning(f"Invalid runnable class: {import_path}")
            except Exception as e:
                self._logger.error(f"Failed to register custom runnable {name}: {e}")

    def register(self, name: str, runnable_class: Type[Runnable]) -> None:
        """Register a custom runnable class.

        Args:
            name: Name to register the runnable under
            runnable_class: The runnable class to register
        """
        if not isinstance(runnable_class, type) or not issubclass(
            runnable_class, Runnable
        ):
            raise ValueError(
                f"runnable_class must be a subclass of Runnable, got {type(runnable_class)}"
            )

        self._custom_registry[name] = runnable_class
        self._logger.info(
            f"Registered custom runnable: {name} -> {runnable_class.__name__}"
        )

    def get_runnable_class(self, name: str) -> Optional[Type[Runnable]]:
        """Get a runnable class by name.

        Args:
            name: Name of the runnable

        Returns:
            The runnable class if found, None otherwise
        """
        # Check custom registry first
        if name in self._custom_registry:
            return self._custom_registry[name]

        # Check built-in registry
        if name in self._builtin_registry:
            return self._builtin_registry[name]

        return None

    def list_available_runnables(self) -> Dict[str, list[str]]:
        """List all available runnables.

        Returns:
            Dictionary with 'custom' and 'builtin' runnable lists
        """
        return {
            "custom": list(self._custom_registry.keys()),
            "builtin": list(self._builtin_registry.keys()),
        }

    def invoke(self, input_data: Union[str, Dict[str, Any]]) -> Runnable:
        """Runnable interface implementation.

        This makes the registry itself a runnable that can be used in LCEL chains.

        Args:
            input_data: Either a runnable name (string) or config dict

        Returns:
            An instance of the requested runnable

        Raises:
            ValueError: If the runnable is not found
            RuntimeError: If instantiation fails
        """
        if isinstance(input_data, str):
            # Simple case: just the runnable name
            runnable_name = input_data
            config = {}
        else:
            # Config dict case
            runnable_name = input_data.get("runnable_name")
            config = input_data.get("config", {})

            if not runnable_name:
                raise ValueError(
                    "input_data must be a string or dict with 'runnable_name'"
                )

        # Get the runnable class
        runnable_class = self.get_runnable_class(runnable_name)
        if not runnable_class:
            available = self.list_available_runnables()
            raise ValueError(
                f"Unknown runnable: {runnable_name}. "
                f"Available custom: {available['custom']}, "
                f"Available builtin: {available['builtin']}"
            )

        try:
            # Instantiate the runnable with the provided config
            runnable = runnable_class(**config)

            # Apply LangChain native features if specified
            if "cache" in config and config["cache"]:
                # Note: This is a placeholder - actual caching would use LangChain's cache system
                self._logger.debug(f"Applied caching to {runnable_name}")

            if "fallbacks" in config and config["fallbacks"]:
                fallback_names = config["fallbacks"]
                fallbacks = []
                for fallback_name in fallback_names:
                    fallback_class = self.get_runnable_class(fallback_name)
                    if fallback_class:
                        fallbacks.append(
                            fallback_class(**config.get("fallback_config", {}))
                        )
                    else:
                        self._logger.warning(
                            f"Fallback runnable not found: {fallback_name}"
                        )

                if fallbacks:
                    runnable = runnable.with_fallbacks(fallbacks)
                    self._logger.debug(f"Applied fallbacks to {runnable_name}")

            if "retry" in config and config["retry"]:
                retry_config = config["retry"]
                if isinstance(retry_config, dict):
                    runnable = runnable.with_retry(**retry_config)
                else:
                    runnable = runnable.with_retry()
                self._logger.debug(f"Applied retry to {runnable_name}")

            return runnable

        except Exception as e:
            raise RuntimeError(f"Failed to instantiate runnable {runnable_name}: {e}")

    async def ainvoke(self, input_data: Union[str, Dict[str, Any]]) -> Runnable:
        """Async version of invoke."""
        return self.invoke(input_data)

    def __repr__(self) -> str:
        """String representation of the registry."""
        custom_count = len(self._custom_registry)
        builtin_count = len(self._builtin_registry)
        return f"RunnableRegistry(custom={custom_count}, builtin={builtin_count})"
