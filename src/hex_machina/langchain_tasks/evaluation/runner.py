"""
Evaluation runner for LangChain tasks using LangSmith's aevaluate.

This module provides the core evaluation functionality, following LangSmith's
evaluation philosophy and patterns.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from langsmith import Client, aevaluate

from .registry import evaluator_registry


class EvaluationRunner:
    """
    Runner for executing evaluations on datasets.

    Uses LangSmith's aevaluate() as the core engine for both
    step-level and task-level evaluations.
    """

    def __init__(self, client: Optional[Client] = None):
        """Initialize the evaluation runner.

        Args:
            client: LangSmith client. If None, creates a new one.
        """
        self.client = client or Client()
        self._logger = logging.getLogger("langchain_tasks.evaluation.runner")

    async def evaluate_step(
        self,
        step_name: str,
        dataset_name: str,
        evaluators: List[Dict[str, Any]],
        experiment_prefix: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Any:
        """Evaluate a specific step using its dataset.

        Args:
            step_name: Name of the step to evaluate
            dataset_name: Name of the dataset to evaluate on
            evaluators: List of evaluator configurations
            experiment_prefix: Prefix for the experiment name
            metadata: Additional metadata for the experiment
            **kwargs: Additional arguments for aevaluate

        Returns:
            Evaluation results from LangSmith
        """
        try:
            self._logger.info(
                f"Evaluating step '{step_name}' on dataset '{dataset_name}'"
            )

            # Prepare evaluators
            prepared_evaluators = []
            for eval_config in evaluators:
                evaluator_name = eval_config["name"]
                evaluator_kwargs = eval_config.get("hyperparameters", {})

                # Get the evaluator from registry
                evaluator = evaluator_registry.get_evaluator(
                    evaluator_name, **evaluator_kwargs
                )
                prepared_evaluators.append(evaluator)

            # Prepare experiment metadata
            experiment_metadata = {
                "step_name": step_name,
                "evaluation_type": "step_level",
                **(metadata or {}),
            }

            # Run evaluation using LangSmith's aevaluate
            results = await aevaluate(
                target=lambda x: x,  # Identity function for dataset evaluation
                data=dataset_name,
                evaluators=prepared_evaluators,
                experiment_prefix=experiment_prefix or f"{step_name}_evaluation",
                description=f"Evaluation of step '{step_name}'",
                metadata=experiment_metadata,
                **kwargs,
            )

            self._logger.info(f"Step evaluation completed for '{step_name}'")
            return results

        except Exception as e:
            self._logger.error(f"Step evaluation failed for '{step_name}': {e}")
            raise

    async def evaluate_task(
        self,
        task_name: str,
        dataset_name: str,
        evaluators: List[Dict[str, Any]],
        experiment_prefix: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Any:
        """Evaluate the complete task using its dataset.

        Args:
            task_name: Name of the task to evaluate
            dataset_name: Name of the dataset to evaluate on
            evaluators: List of evaluator configurations
            experiment_prefix: Prefix for the experiment name
            metadata: Additional metadata for the experiment
            **kwargs: Additional arguments for aevaluate

        Returns:
            Evaluation results from LangSmith
        """
        try:
            self._logger.info(
                f"Evaluating task '{task_name}' on dataset '{dataset_name}'"
            )

            # Prepare evaluators
            prepared_evaluators = []
            for eval_config in evaluators:
                evaluator_name = eval_config["name"]
                evaluator_kwargs = eval_config.get("hyperparameters", {})

                # Get the evaluator from registry
                evaluator = evaluator_registry.get_evaluator(
                    evaluator_name, **evaluator_kwargs
                )
                prepared_evaluators.append(evaluator)

            # Prepare experiment metadata
            experiment_metadata = {
                "task_name": task_name,
                "evaluation_type": "task_level",
                **(metadata or {}),
            }

            # Run evaluation using LangSmith's aevaluate
            results = await aevaluate(
                target=lambda x: x,  # Identity function for dataset evaluation
                data=dataset_name,
                evaluators=prepared_evaluators,
                experiment_prefix=experiment_prefix or f"{task_name}_evaluation",
                description=f"Evaluation of task '{task_name}'",
                metadata=experiment_metadata,
                **kwargs,
            )

            self._logger.info(f"Task evaluation completed for '{task_name}'")
            return results

        except Exception as e:
            self._logger.error(f"Task evaluation failed for '{task_name}': {e}")
            raise

    async def evaluate_experiment(
        self,
        experiment_name: str,
        step_evaluations: Dict[str, List[Dict[str, Any]]],
        task_evaluations: List[Dict[str, Any]],
        dataset_pattern: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Evaluate a complete experiment with multiple steps and task-level evaluation.

        Args:
            experiment_name: Name of the experiment
            step_evaluations: Evaluation configs for each step
            task_evaluations: Evaluation configs for the task
            dataset_pattern: Pattern to match datasets (e.g., "{experiment_name}_{step_name}_*")
            **kwargs: Additional arguments for aevaluate

        Returns:
            Dictionary with evaluation results for each component
        """
        try:
            self._logger.info(f"Evaluating experiment '{experiment_name}'")

            results = {
                "experiment_name": experiment_name,
                "step_evaluations": {},
                "task_evaluations": None,
            }

            # Evaluate each step
            for step_name, evaluators in step_evaluations.items():
                # Find datasets for this step
                step_datasets = self._find_step_datasets(experiment_name, step_name)

                if not step_datasets:
                    self._logger.warning(f"No datasets found for step '{step_name}'")
                    continue

                # Evaluate each dataset for this step
                step_results = []
                for dataset_name in step_datasets:
                    step_result = await self.evaluate_step(
                        step_name=step_name,
                        dataset_name=dataset_name,
                        evaluators=evaluators,
                        experiment_prefix=f"{experiment_name}_{step_name}",
                        metadata={"experiment_name": experiment_name},
                        **kwargs,
                    )
                    step_results.append(
                        {"dataset": dataset_name, "results": step_result}
                    )

                results["step_evaluations"][step_name] = step_results

            # Evaluate task-level if specified
            if task_evaluations:
                task_datasets = self._find_task_datasets(experiment_name)

                if task_datasets:
                    task_results = []
                    for dataset_name in task_datasets:
                        task_result = await self.evaluate_task(
                            task_name=experiment_name,
                            dataset_name=dataset_name,
                            evaluators=task_evaluations,
                            experiment_prefix=f"{experiment_name}_task",
                            metadata={"experiment_name": experiment_name},
                            **kwargs,
                        )
                        task_results.append(
                            {"dataset": dataset_name, "results": task_result}
                        )

                    results["task_evaluations"] = task_results

            self._logger.info(
                f"Experiment evaluation completed for '{experiment_name}'"
            )
            return results

        except Exception as e:
            self._logger.error(
                f"Experiment evaluation failed for '{experiment_name}': {e}"
            )
            raise

    def _find_step_datasets(self, experiment_name: str, step_name: str) -> List[str]:
        """Find datasets for a specific step in an experiment.

        Args:
            experiment_name: Name of the experiment
            step_name: Name of the step

        Returns:
            List of dataset names
        """
        try:
            # List all datasets and filter by pattern
            all_datasets = self.client.list_datasets()

            step_datasets = []
            for dataset in all_datasets:
                if (
                    dataset.name.startswith(f"{experiment_name}_{step_name}_")
                    and "_task_" not in dataset.name
                ):
                    step_datasets.append(dataset.name)

            return sorted(step_datasets)

        except Exception as e:
            self._logger.warning(f"Failed to find step datasets: {e}")
            return []

    def _find_task_datasets(self, experiment_name: str) -> List[str]:
        """Find task-level datasets for an experiment.

        Args:
            experiment_name: Name of the experiment

        Returns:
            List of dataset names
        """
        try:
            # List all datasets and filter by pattern
            all_datasets = self.client.list_datasets()

            task_datasets = []
            for dataset in all_datasets:
                if dataset.name.startswith(f"{experiment_name}_task_"):
                    task_datasets.append(dataset.name)

            return sorted(task_datasets)

        except Exception as e:
            self._logger.warning(f"Failed to find task datasets: {e}")
            return []

    def run_sync(self, coro):
        """Run an async coroutine synchronously.

        Args:
            coro: Async coroutine to run

        Returns:
            Result of the coroutine
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, we can't use run_until_complete
                # This is a fallback for sync contexts
                return asyncio.create_task(coro)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create a new one
            return asyncio.run(coro)
