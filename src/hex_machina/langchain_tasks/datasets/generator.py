"""
Dataset generator for LangChain tasks.

This module provides functionality to create and manage LangSmith datasets
for individual steps with automatic split creation.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langsmith import Client, schemas

from .models import DatasetDefinition


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

    def create_step_range_dataset(
        self,
        task_name: str,
        dataset_def: "DatasetDefinition",
        run_id: str,
    ) -> Optional[schemas.Dataset]:
        """Create a step-range dataset for evaluating step ranges.

        Args:
            task_name: Name of the task
            dataset_def: Dataset definition with input/output step mappings
            run_id: Task run identifier

        Returns:
            Created dataset if successful, None otherwise
        """
        try:
            # Generate dataset name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dataset_name = f"{task_name}_{dataset_def.name}_{timestamp}"

            # Check if dataset already exists
            if dataset_name in self._dataset_cache:
                self._logger.debug(f"Dataset {dataset_name} already exists in cache")
                return self._dataset_cache[dataset_name]

            # Create dataset
            dataset = self.client.create_dataset(
                dataset_name=dataset_name,
                description=dataset_def.description
                or f"Step-range dataset for {dataset_def.name} in {task_name}",
            )

            # Cache the dataset
            self._dataset_cache[dataset_name] = dataset
            self._example_counts[dataset_name] = 0

            self._logger.info(
                f"Created step-range dataset: {dataset_name} (ID: {dataset.id})"
            )
            return dataset

        except Exception as e:
            self._logger.error(
                f"Failed to create step-range dataset {dataset_def.name}: {e}"
            )
            return None

    def bulk_add_step_range_examples(
        self,
        dataset: schemas.Dataset,
        examples_data: List[Dict[str, Any]],
        run_id: str,
        dataset_def: "DatasetDefinition",
        task_name: str,
    ) -> Optional[List[schemas.Example]]:
        """Bulk add examples to a step-range dataset using create_examples.

        Args:
            dataset: The dataset to add examples to
            examples_data: List of dicts with 'inputs' and 'outputs' keys
            run_id: Task run identifier
            dataset_def: Dataset definition
            task_name: Name of the task

        Returns:
            List of created examples if successful, None otherwise
        """
        if not examples_data:
            return []

        try:
            # Prepare metadata for all examples
            base_metadata = {
                "run_id": run_id,
                "task_name": task_name,
                "input_step": dataset_def.input_step,
                "output_step": dataset_def.output_step,
                "dataset_name": dataset_def.name,
                "timestamp": datetime.now().isoformat(),
                "example_type": "step_range_execution",
            }

            # Prepare examples for bulk creation
            examples_to_create = []
            for i, example_data in enumerate(examples_data):
                example_metadata = base_metadata.copy()
                example_metadata["example_index"] = i

                examples_to_create.append(
                    {
                        "inputs": example_data["inputs"],
                        "outputs": example_data["outputs"],
                        "metadata": example_metadata,
                    }
                )

            # Bulk create all examples at once using dataset_id parameter
            self._logger.info(f"Creating {len(examples_to_create)} examples...")

            try:
                created_examples = self.client.create_examples(
                    dataset_id=dataset.id,
                    examples=examples_to_create,
                )
                self._logger.info(f"LangSmith API response: {created_examples}")

                # Extract the actual count from the response
                if hasattr(created_examples, "count"):
                    actual_count = created_examples.count
                elif isinstance(created_examples, dict) and "count" in created_examples:
                    actual_count = created_examples["count"]
                else:
                    actual_count = len(examples_to_create)  # Fallback

                self._logger.info(f"Created {actual_count} examples")

            except Exception as e:
                self._logger.error(f"Failed to create examples via bulk API: {e}")
                # Fallback: try creating examples one by one
                self._logger.info("Falling back to individual example creation...")
                created_examples = []
                for i, example_data in enumerate(examples_to_create):
                    try:
                        example = self.client.create_example(
                            dataset_id=dataset.id,
                            inputs=example_data["inputs"],
                            outputs=example_data["outputs"],
                            metadata=example_data["metadata"],
                        )
                        created_examples.append(example)
                        self._logger.debug(
                            f"Created example {i+1}/{len(examples_to_create)}"
                        )
                    except Exception as individual_error:
                        self._logger.error(
                            f"Failed to create example {i+1}: {individual_error}"
                        )
                        continue
                actual_count = len(created_examples)

            # Update example count with the actual count from the response
            dataset_name = dataset.name
            previous_count = self._example_counts.get(dataset_name, 0)
            new_count = previous_count + actual_count
            self._example_counts[dataset_name] = new_count

            self._logger.info(
                f"Added {actual_count} examples to dataset {dataset_name}. "
                f"Total count: {new_count}"
            )

            # Check if we should create a split
            self._logger.info(f"Checking split creation for dataset {dataset_name}")
            self._maybe_create_split(dataset, dataset_name)

            return created_examples

        except Exception as e:
            self._logger.warning(
                f"Failed to bulk add examples to step-range dataset {dataset.name}: {e}"
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

        self._logger.info(
            f"Split creation check for dataset {dataset_name}: "
            f"example_count={example_count}, threshold={small_split_threshold}"
        )

        if example_count >= small_split_threshold:
            try:
                self._logger.info(
                    f"Threshold met! Creating '{default_split_name}' split..."
                )

                # Get the first 3 examples for the split
                examples = self.client.list_examples(
                    dataset_id=dataset.id, limit=small_split_threshold
                )

                # Convert generator to list to get length and slice
                examples_list = list(examples)
                self._logger.info(f"Found {len(examples_list)} examples in dataset")

                # Create split with the first 3 examples
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
                self._logger.error(
                    f"Failed to create split for dataset {dataset_name}: {e}"
                )
        else:
            self._logger.info(
                f"Split creation skipped: {example_count} examples < {small_split_threshold} threshold"
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
