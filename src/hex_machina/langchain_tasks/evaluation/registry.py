"""
Evaluator registry for LangChain task evaluation.

This registry manages both built-in LangSmith evaluators and custom evaluators,
following LangSmith's evaluation philosophy.
"""

import logging
from typing import Any, Callable, Dict, List

# Import available evaluators from langchain
try:
    from langchain.evaluation.criteria import CriteriaEvalChain

    CRITERIA_AVAILABLE = True
except ImportError:
    CRITERIA_AVAILABLE = False

try:
    from langchain.evaluation.qa import QAEvalChain

    QA_AVAILABLE = True
except ImportError:
    QA_AVAILABLE = False

try:
    from langchain.evaluation.rag import RAGEvalChain

    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


class EvaluatorRegistry:
    """
    Registry for evaluation functions and chains.

    Supports both built-in LangSmith evaluators and custom evaluators.
    """

    def __init__(self):
        """Initialize the evaluator registry."""
        self._builtin_evaluators: Dict[str, Any] = {}
        self._custom_evaluators: Dict[str, Callable] = {}
        self._logger = logging.getLogger("langchain_tasks.evaluation.registry")

        # Register built-in evaluators
        self._register_builtin_evaluators()

    def _register_builtin_evaluators(self):
        """Register built-in LangSmith evaluators."""
        try:
            # Criteria-based evaluation
            if CRITERIA_AVAILABLE:
                self._builtin_evaluators["criteria"] = CriteriaEvalChain

            # QA evaluation
            if QA_AVAILABLE:
                self._builtin_evaluators["qa_correctness"] = QAEvalChain

            # RAG evaluation
            if RAG_AVAILABLE:
                self._builtin_evaluators["rag"] = RAGEvalChain

            self._logger.info(
                f"Registered {len(self._builtin_evaluators)} built-in evaluators"
            )

        except Exception as e:
            self._logger.warning(f"Could not import some built-in evaluators: {e}")

    def register_custom_evaluator(self, name: str, evaluator: Callable):
        """Register a custom evaluator function.

        Args:
            name: Name of the evaluator
            evaluator: Function that takes (run: Run, example: Example) and returns dict
        """
        self._custom_evaluators[name] = evaluator
        self._logger.info(f"Registered custom evaluator: {name}")

    def get_evaluator(self, name: str, **kwargs) -> Callable:
        """Get an evaluator by name.

        Args:
            name: Name of the evaluator
            **kwargs: Parameters to pass to the evaluator

        Returns:
            Evaluator function or chain

        Raises:
            ValueError: If evaluator not found
        """
        # Check custom evaluators first
        if name in self._custom_evaluators:
            return self._custom_evaluators[name]

        # Check built-in evaluators
        if name in self._builtin_evaluators:
            evaluator_class = self._builtin_evaluators[name]
            try:
                return evaluator_class(**kwargs)
            except Exception as e:
                self._logger.error(
                    f"Failed to instantiate built-in evaluator {name}: {e}"
                )
                raise ValueError(f"Failed to instantiate evaluator {name}: {e}")

        # Check if it's a criteria evaluator with specific criteria
        if name.startswith("criteria:"):
            criteria_name = name.split(":", 1)[1]
            try:
                # Import CriteriaEvalChain if available
                if CRITERIA_AVAILABLE:
                    from langchain.evaluation.criteria import CriteriaEvalChain

                    return CriteriaEvalChain(criteria=criteria_name, **kwargs)
                else:
                    raise ValueError(
                        "CriteriaEvalChain not available - langchain.evaluation not installed"
                    )
            except Exception as e:
                self._logger.error(
                    f"Failed to create criteria evaluator for {criteria_name}: {e}"
                )
                raise ValueError(
                    f"Failed to create criteria evaluator for {criteria_name}: {e}"
                )

        raise ValueError(
            f"Evaluator '{name}' not found. Available: {list(self._builtin_evaluators.keys()) + list(self._custom_evaluators.keys())}"
        )

    def list_evaluators(self) -> Dict[str, List[str]]:
        """List all available evaluators.

        Returns:
            Dictionary with built-in and custom evaluators
        """
        return {
            "builtin": list(self._builtin_evaluators.keys()),
            "custom": list(self._custom_evaluators.keys()),
        }

    def get_evaluator_info(self, name: str) -> Dict[str, Any]:
        """Get information about a specific evaluator.

        Args:
            name: Name of the evaluator

        Returns:
            Dictionary with evaluator information
        """
        if name in self._custom_evaluators:
            evaluator = self._custom_evaluators[name]
            return {
                "type": "custom",
                "name": name,
                "function": evaluator.__name__,
                "module": evaluator.__module__,
            }

        if name in self._builtin_evaluators:
            evaluator_class = self._builtin_evaluators[name]
            return {
                "type": "builtin",
                "name": name,
                "class": evaluator_class.__name__,
                "module": evaluator_class.__module__,
            }

        if name.startswith("criteria:"):
            criteria_name = name.split(":", 1)[1]
            return {
                "type": "builtin",
                "name": name,
                "class": "CriteriaEvalChain",
                "criteria": criteria_name,
            }

        raise ValueError(f"Evaluator '{name}' not found")


# Global registry instance
evaluator_registry = EvaluatorRegistry()
