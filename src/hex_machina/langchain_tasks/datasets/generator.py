"""
Dataset generator for LangChain tasks.

This module provides functionality to create and manage LangSmith datasets
for individual steps with automatic split creation.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from langsmith import Client, schemas

from .models import StepDataset


class DatasetGenerator:
    """
    Generator for creating and managing LangSmith datasets.

    This class handles:
    - Creating step-level datasets
    - Adding examples with run_id grouping
    - Automatic split creation
    - Dataset naming and organization
    """

    def __init__(
        self, client: Optional[Client] = None, config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the dataset generator.

        Args:
            client: LangSmith client. If None, creates a new one.
            config: Task-level dataset configuration.
        """
        self.client = client or Client()
        self.config = config or {}
        self._logger = logging.getLogger("langchain_tasks.datasets.generator")

        # Track datasets and example counts
        self._dataset_cache: Dict[str, schemas.Dataset] = {}
        self._example_counts: Dict[str, int] = {}

        self._logger.info("DatasetGenerator initialized")

    def create_step_dataset(
        self,
        task_name: str,
        step_name: str,
        step_config: StepDataset,
        run_id: str,
        grouped: bool = False,
    ) -> Optional[schemas.Dataset]:
        """Create or get a dataset for a specific step.

        Args:
            task_name: Name of the task
            step_name: Name of the step
            step_config: Step dataset configuration
            run_id: Unique identifier for the task run

        Returns:
            The dataset if creation is enabled, None otherwise
        """
        if not step_config.enabled:
            return None

        # Generate dataset name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = f"{task_name}_{step_name}_{timestamp}"

        # Check if we already have this dataset
        if dataset_name in self._dataset_cache:
            return self._dataset_cache[dataset_name]

        try:
            # Create the dataset
            description = (
                step_config.description
                or f"Dataset for {step_name} step of {task_name}"
            )

            dataset = self.client.create_dataset(
                dataset_name=dataset_name,
                description=description,
                data_type=schemas.DataType.kv,
            )

            # Cache the dataset and initialize example count
            self._dataset_cache[dataset_name] = dataset
            self._example_counts[dataset_name] = 0

            self._logger.info(f"Created dataset: {dataset_name} (ID: {dataset.id})")
            return dataset

        except Exception as e:
            self._logger.warning(f"Failed to create dataset {dataset_name}: {e}")
            return None

    def create_task_dataset(
        self,
        task_name: str,
        run_id: str,
    ) -> Optional[schemas.Dataset]:
        """Create or get a dataset for the entire task.

        Args:
            task_name: Name of the task
            task_config: Task dataset configuration
            run_id: Unique identifier for the task run

        Returns:
            The dataset if creation is enabled, None otherwise
        """
        # Generate dataset name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = f"{task_name}_task_{timestamp}"

        # Check if we already have this dataset
        if dataset_name in self._dataset_cache:
            return self._dataset_cache[dataset_name]

        try:
            # Create the dataset
            description = f"Dataset for complete task execution: {task_name}"

            dataset = self.client.create_dataset(
                dataset_name=dataset_name,
                description=description,
                data_type=schemas.DataType.kv,
            )

            # Cache the dataset and initialize example count
            self._dataset_cache[dataset_name] = dataset
            self._example_counts[dataset_name] = 0

            self._logger.info(
                f"Created task dataset: {dataset_name} (ID: {dataset.id})"
            )
            return dataset

        except Exception as e:
            self._logger.warning(f"Failed to create task dataset {dataset_name}: {e}")
            return None

    def add_task_example(
        self,
        dataset: schemas.Dataset,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        run_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[schemas.Example]:
        """Add an example to a task-level dataset.

        Args:
            dataset: The dataset to add the example to
            inputs: Input data for the task
            outputs: Output data from the task
            run_id: Unique identifier for the task run
            metadata: Additional metadata

        Returns:
            The created example if successful, None otherwise
        """
        try:
            # Prepare metadata
            example_metadata = {
                "run_id": run_id,
                "example_type": "task_level",
                "created_at": datetime.now().isoformat(),
            }
            if metadata:
                example_metadata.update(metadata)

            # Create the example
            example = self.client.create_example(
                inputs=inputs,
                outputs=outputs,
                dataset_id=dataset.id,
                metadata=example_metadata,
            )

            # Update example count
            dataset_name = dataset.name
            self._example_counts[dataset_name] = (
                self._example_counts.get(dataset_name, 0) + 1
            )

            self._logger.debug(
                f"Added task example to dataset {dataset_name} (run_id: {run_id})"
            )

            # Check if we should create a split
            self._maybe_create_split(dataset, dataset_name)

            return example

        except Exception as e:
            self._logger.warning(
                f"Failed to add task example to dataset {dataset.name}: {e}"
            )
            return None

    def add_step_example(
        self,
        dataset: schemas.Dataset,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        run_id: str,
        step_name: str,
        task_name: str,
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[schemas.Example]:
        """Add an example to a step dataset.

        Args:
            dataset: The dataset to add the example to
            inputs: Step inputs
            outputs: Step outputs
            run_id: Task run identifier
            step_name: Name of the step
            task_name: Name of the task
            additional_metadata: Any additional metadata

        Returns:
            The created example if successful, None otherwise
        """
        try:
            # Prepare metadata
            metadata = {
                "run_id": run_id,
                "step_name": step_name,
                "task_name": task_name,
                "timestamp": datetime.now().isoformat(),
                "example_type": "step_execution",
            }

            if additional_metadata:
                metadata.update(additional_metadata)

            # Create the example
            example = self.client.create_example(
                inputs=inputs, outputs=outputs, dataset_id=dataset.id, metadata=metadata
            )

            # Update example count
            dataset_name = dataset.name
            self._example_counts[dataset_name] = (
                self._example_counts.get(dataset_name, 0) + 1
            )

            self._logger.debug(
                f"Added example to dataset {dataset_name} (run_id: {run_id})"
            )

            self._maybe_create_split(dataset, dataset_name)

            return example

        except Exception as e:
            self._logger.warning(
                f"Failed to add example to dataset {dataset.name}: {e}"
            )
            return None

    def _maybe_create_split(self, dataset: schemas.Dataset, dataset_name: str) -> None:
        """Create a split if the threshold is met.

        Args:
            dataset: The dataset to potentially create a split for
            dataset_name: Name of the dataset for logging
        """
        default_split_name = "small"
        small_split_threshold = 3
        example_count = self._example_counts.get(dataset_name, 0)

        if example_count > small_split_threshold:
            try:
                # Get the first 3 examples for the split
                examples = self.client.list_examples(
                    dataset_id=dataset.id, limit=small_split_threshold
                )

                # Convert generator to list to get length and slice
                examples_list = list(examples)

                # Get the first N examples for the split
                split_examples = examples_list[:small_split_threshold]

                self.client.update_dataset_splits(
                    dataset_id=dataset.id,
                    split_name=default_split_name,
                    example_ids=[str(example.id) for example in split_examples],
                )
                self._logger.info(
                    f"Created '{default_split_name}' split for dataset {dataset_name} "
                    f"with {len(split_examples)} examples"
                )

            except Exception as e:
                self._logger.warning(
                    f"Failed to prepare split for dataset {dataset_name}: {e}"
                )

    def get_dataset_stats(self) -> Dict[str, Any]:
        """Get statistics about managed datasets.

        Returns:
            Dictionary with dataset statistics
        """
        return {
            "total_datasets": len(self._dataset_cache),
            "dataset_names": list(self._dataset_cache.keys()),
            "example_counts": self._example_counts.copy(),
            "config": self.config,
        }

    def cleanup_cache(self) -> None:
        """Clear the internal dataset cache."""
        self._dataset_cache.clear()
        self._example_counts.clear()
        self._logger.info("Dataset cache cleared")
