"""
Experiment runner for LangChain tasks with multiple variations.

This module handles the execution of experiments with multiple task configurations,
generating datasets for each variation and preparing them for evaluation.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..builder import TaskBuilder
from ..config.models import ExperimentConfig, TaskConfig
from ..datasets import StepDatasetManager


class ExperimentRunner:
    """
    Runner for executing experiments with multiple task variations.

    Generates all possible task variations from multiple values in the config,
    executes each variation, and generates datasets for evaluation.
    """

    def __init__(
        self,
        task_builder: Optional[TaskBuilder] = None,
        dataset_manager: Optional[StepDatasetManager] = None,
    ):
        """Initialize the experiment runner.

        Args:
            task_builder: Task builder for creating and executing tasks
            dataset_manager: Dataset manager for generating datasets
        """
        self.task_builder = task_builder or TaskBuilder()
        self.dataset_manager = dataset_manager
        self._logger = logging.getLogger("langchain_tasks.experiments.runner")

    def run_experiment(
        self, experiment_config: ExperimentConfig, inputs: Dict[str, Any], **kwargs
    ) -> Dict[str, Any]:
        """Run a complete experiment with multiple task variations.

        Args:
            experiment_config: Experiment configuration
            inputs: Input data for the tasks
            **kwargs: Additional arguments for task execution

        Returns:
            Dictionary with experiment results and dataset information
        """
        try:
            self._logger.info(f"Starting experiment: {experiment_config.name}")

            # Generate all task variations
            task_variations = experiment_config.generate_task_variations()
            self._logger.info(f"Generated {len(task_variations)} task variations")

            # Execute each variation
            results = {
                "experiment_name": experiment_config.name,
                "total_variations": len(task_variations),
                "variations": [],
                "datasets_created": [],
            }

            for i, task_config in enumerate(task_variations):
                self._logger.info(f"Executing variation {i+1}/{len(task_variations)}")

                # Execute the task variation
                variation_result = self._execute_task_variation(
                    task_config=task_config,
                    variation_index=i,
                    experiment_name=experiment_config.name,
                    inputs=inputs,
                    **kwargs,
                )

                results["variations"].append(variation_result)

                # Generate datasets if enabled
                if self.dataset_manager:
                    datasets = self._generate_variation_datasets(
                        task_config=task_config,
                        variation_index=i,
                        experiment_name=experiment_config.name,
                        variation_result=variation_result,
                    )
                    results["datasets_created"].extend(datasets)

            self._logger.info(f"Experiment completed: {experiment_config.name}")
            return results

        except Exception as e:
            self._logger.error(f"Experiment failed: {e}")
            raise

    def _execute_task_variation(
        self,
        task_config: TaskConfig,
        variation_index: int,
        experiment_name: str,
        inputs: Dict[str, Any],
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute a single task variation.

        Args:
            task_config: Task configuration for this variation
            variation_index: Index of this variation
            experiment_name: Name of the experiment
            inputs: Input data for the task
            **kwargs: Additional arguments for task execution

        Returns:
            Dictionary with variation execution results
        """
        try:
            # Add variation metadata
            task_config.metadata.update(
                {
                    "experiment_name": experiment_name,
                    "variation_index": variation_index,
                    "variation_timestamp": datetime.now().isoformat(),
                }
            )

            # Execute the task
            if hasattr(self.task_builder, "invoke_with_tracing"):
                result = self.task_builder.invoke_with_tracing(task_config, inputs)
            else:
                # Fallback to regular invoke
                task = self.task_builder.invoke(task_config)
                result = task.invoke(inputs)

            return {
                "variation_index": variation_index,
                "task_name": task_config.name,
                "inputs": inputs,
                "result": result,
                "metadata": task_config.metadata,
                "success": True,
            }

        except Exception as e:
            self._logger.error(f"Variation {variation_index} failed: {e}")
            return {
                "variation_index": variation_index,
                "task_name": task_config.name,
                "inputs": inputs,
                "error": str(e),
                "success": False,
            }

    def _generate_variation_datasets(
        self,
        task_config: TaskConfig,
        variation_index: int,
        experiment_name: str,
        variation_result: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate datasets for a task variation.

        Args:
            task_config: Task configuration for this variation
            variation_index: Index of this variation
            experiment_name: Name of the experiment
            variation_result: Results from task execution

        Returns:
            List of dataset information
        """
        if not self.dataset_manager:
            return []

        try:
            # Start task execution in dataset manager
            run_id = self.dataset_manager.start_task_execution(
                f"{experiment_name}_{variation_index}"
            )

            datasets = []

            # Generate step-level datasets
            for step_config in task_config.steps:
                if step_config.dataset:
                    # Create step dataset with proper naming
                    dataset_name = f"{experiment_name}_{step_config.name}_{variation_index}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                    # For now, we'll create a placeholder dataset
                    # In practice, this would use the actual step execution data
                    dataset_info = {
                        "name": dataset_name,
                        "step_name": step_config.name,
                        "variation_index": variation_index,
                        "type": "step_level",
                        "run_id": run_id,
                    }
                    datasets.append(dataset_info)

            # Generate task-level dataset if enabled
            if task_config.dataset:
                dataset_name = f"{experiment_name}_task_{variation_index}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                dataset_info = {
                    "name": dataset_name,
                    "step_name": "task",
                    "variation_index": variation_index,
                    "type": "task_level",
                    "run_id": run_id,
                }
                datasets.append(dataset_info)

            return datasets

        except Exception as e:
            self._logger.error(
                f"Failed to generate datasets for variation {variation_index}: {e}"
            )
            return []

    def get_experiment_summary(self, experiment_name: str) -> Dict[str, Any]:
        """Get a summary of experiment results and datasets.

        Args:
            experiment_name: Name of the experiment

        Returns:
            Dictionary with experiment summary
        """
        try:
            # This would typically query LangSmith for experiment results
            # For now, return a basic structure
            return {
                "experiment_name": experiment_name,
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "note": "Use LangSmith UI for detailed results",
            }

        except Exception as e:
            self._logger.error(f"Failed to get experiment summary: {e}")
            return {"error": str(e)}

