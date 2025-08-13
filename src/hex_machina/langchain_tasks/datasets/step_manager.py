"""
Step dataset manager for LangChain tasks.

This module manages the creation and population of datasets for individual steps
during task execution.
"""

import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from .generator import DatasetGenerator
from .models import StepDataset


class StepDatasetManager:
    """
    Manager for step-level datasets during task execution.

    This class coordinates:
    - Dataset creation for enabled steps
    - Example collection during step execution
    - Run_id tracking across steps
    - Integration with TaskBuilder
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
        self._step_datasets: Dict[str, Any] = {}  # step_name -> dataset
        self._task_dataset: Optional[Any] = None  # task-level dataset

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
        self._step_datasets.clear()

        self._logger.info(
            f"Started task execution: {task_name} (run_id: {self._current_run_id})"
        )
        return self._current_run_id

    def prepare_step_dataset(
        self, step_name: str, step_config: StepDataset
    ) -> Optional[Any]:
        """Prepare a dataset for a specific step.

        Args:
            step_name: Name of the step
            step_config: Step dataset configuration

        Returns:
            The prepared dataset if enabled, None otherwise
        """
        if not step_config.enabled:
            return None

        if not self._current_run_id or not self._current_task_name:
            self._logger.warning("No active task execution")
            return None

        try:
            dataset = self.generator.create_step_dataset(
                task_name=self._current_task_name,
                step_name=step_name,
                step_config=step_config,
                run_id=self._current_run_id,
            )

            if dataset:
                self._step_datasets[step_name] = dataset
                self._logger.debug(f"Prepared dataset for step: {step_name}")

            return dataset

        except Exception as e:
            self._logger.error(f"Failed to prepare step dataset for {step_name}: {e}")
            return None

    def prepare_task_dataset(self) -> Optional[Any]:
        """Prepare a dataset for the entire task.

        Returns:
            The prepared task dataset if enabled, None otherwise
        """

        if not self._current_run_id or not self._current_task_name:
            self._logger.warning("No active task execution")
            return None

        try:
            dataset = self.generator.create_task_dataset(
                task_name=self._current_task_name,
                run_id=self._current_run_id,
            )

            if dataset:
                self._task_dataset = dataset
                self._logger.debug(
                    f"Prepared task-level dataset for: {self._current_task_name}"
                )

            return dataset

        except Exception as e:
            self._logger.warning(f"Failed to prepare task dataset: {e}")
            return None

    def record_task_execution(
        self,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """Record a task execution in the task-level dataset.

        Args:
            inputs: Input data for the task
            outputs: Output data from the task
            metadata: Additional metadata

        Returns:
            The created example if successful, None otherwise
        """
        if not self._task_dataset:
            self._logger.warning("No task dataset available")
            return None

        if not self._current_run_id:
            self._logger.warning("No active task execution")
            return None

        try:
            # Add task-level metadata
            task_metadata = {
                "task_name": self._current_task_name,
                "run_id": self._current_run_id,
                "step_count": len(self._step_datasets),
                "step_names": list(self._step_datasets.keys()),
            }
            if metadata:
                task_metadata.update(metadata)

            example = self.generator.add_task_example(
                dataset=self._task_dataset,
                inputs=inputs,
                outputs=outputs,
                run_id=self._current_run_id,
                metadata=task_metadata,
            )

            if example:
                self._logger.debug(
                    f"Recorded task execution in dataset: {self._task_dataset.name}"
                )

            return example

        except Exception as e:
            self._logger.error(f"Failed to record task execution: {e}")
            return None

    def record_step_execution(
        self,
        step_name: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """Record a step execution in its dataset.

        Args:
            step_name: Name of the step that was executed
            inputs: Inputs to the step
            outputs: Outputs from the step
            additional_metadata: Any additional metadata

        Returns:
            The created example if successful, None otherwise
        """
        if step_name not in self._step_datasets:
            self._logger.debug(f"No dataset for step: {step_name}")
            return None

        if not self._current_run_id or not self._current_task_name:
            self._logger.warning("No active task execution")
            return None

        try:
            dataset = self._step_datasets[step_name]

            example = self.generator.add_step_example(
                dataset=dataset,
                inputs=inputs,
                outputs=outputs,
                run_id=self._current_run_id,
                step_name=step_name,
                task_name=self._current_task_name,
                additional_metadata=additional_metadata,
            )

            if example:
                self._logger.debug(f"Recorded execution for step: {step_name}")

            return example

        except Exception as e:
            self._logger.warning(
                f"Failed to record execution for step {step_name}: {e}"
            )
            return None

    def end_task_execution(self) -> Dict[str, Any]:
        """End the current task execution and return summary.

        Returns:
            Summary of datasets created and examples added
        """
        if not self._current_run_id:
            return {"error": "No active task execution"}

        summary = {
            "run_id": self._current_run_id,
            "task_name": self._current_task_name,
            "step_datasets": {},
            "total_examples": 0,
        }

        # Collect information about each step's dataset
        for step_name, dataset in self._step_datasets.items():
            step_summary = {
                "dataset_id": str(dataset.id),
                "dataset_name": dataset.name,
                "example_count": self.generator._example_counts.get(dataset.name, 0),
            }
            summary["step_datasets"][step_name] = step_summary
            summary["total_examples"] += step_summary["example_count"]

        self._logger.info(
            f"Ended task execution: {self._current_task_name} "
            f"(run_id: {self._current_run_id}, examples: {summary['total_examples']})"
        )

        # Reset for next execution
        self._current_run_id = None
        self._current_task_name = None
        self._step_datasets.clear()

        return summary

    def get_current_status(self) -> Dict[str, Any]:
        """Get current status of the manager.

        Returns:
            Current status information with dataset statistics
        """
        generator_stats = self.generator.get_dataset_stats()

        return {
            "active_task": self._current_task_name,
            "active_run_id": self._current_run_id,
            "step_datasets": list(self._step_datasets.keys()),
            "generator_stats": generator_stats,
            # Add direct access to key stats for convenience
            "total_datasets": generator_stats.get("total_datasets", 0),
            "dataset_names": generator_stats.get("dataset_names", []),
            "total_examples": sum(generator_stats.get("example_counts", {}).values()),
        }
