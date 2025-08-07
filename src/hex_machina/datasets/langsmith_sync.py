"""LangSmith synchronization for datasets."""

import logging
import json
from typing import List, Dict, Any, Optional
from langsmith import Client
from src.hex_machina.storage.models import DatasetExampleDB

logger = logging.getLogger(__name__)


class LangSmithSync:
    """Handles synchronization with LangSmith datasets."""

    def __init__(self):
        """Initialize LangSmith client."""
        try:
            self.client = Client()
            logger.info("LangSmith client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize LangSmith client: {e}")
            self.client = None

    def create_dataset(
        self,
        name: str,
        description: Optional[str] = None,
        data_type: str = "kv",
    ) -> Any:
        """Create dataset in LangSmith."""
        if not self.client:
            raise RuntimeError("LangSmith client not available")

        try:
            dataset = self.client.create_dataset(
                dataset_name=name,
                description=description or f"Dataset: {name}",
            )
            logger.info(f"Created LangSmith dataset: {dataset.id}")
            return dataset
        except Exception as e:
            logger.error(f"Failed to create LangSmith dataset: {e}")
            raise

    def add_examples_to_dataset(
        self,
        dataset_id: str,
        examples: List[DatasetExampleDB],
    ) -> None:
        """Add examples to LangSmith dataset."""
        if not self.client:
            raise RuntimeError("LangSmith client not available")

        try:
            # Prepare examples for LangSmith
            langsmith_examples = []
            for example in examples:
                langsmith_example = {
                    "inputs": example.inputs,
                    "outputs": example.outputs or {},
                    "metadata": example.example_metadata or {},
                }
                langsmith_examples.append(langsmith_example)

            # Add examples in bulk
            self.client.create_examples(
                dataset_id=dataset_id,
                examples=langsmith_examples,
            )
            logger.info(f"Added {len(examples)} examples to LangSmith dataset {dataset_id}")
        except Exception as e:
            logger.error(f"Failed to add examples to LangSmith dataset: {e}")
            raise

    def update_examples_split(
        self,
        dataset_id: str,
        examples: List[DatasetExampleDB],
        new_split: str,
    ) -> None:
        """Update examples split in LangSmith."""
        if not self.client:
            raise RuntimeError("LangSmith client not available")

        try:
            # Update each example's split
            for example in examples:
                if example.langsmith_example_id:
                    self.client.update_example(
                        example_id=example.langsmith_example_id,
                        split=new_split,
                    )
            logger.info(f"Updated split to '{new_split}' for {len(examples)} examples")
        except Exception as e:
            logger.error(f"Failed to update examples split in LangSmith: {e}")
            raise

    def delete_dataset(self, dataset_id: str) -> None:
        """Delete dataset from LangSmith."""
        if not self.client:
            logger.warning("LangSmith client not available, skipping deletion")
            return

        try:
            # Note: LangSmith Python client doesn't have a direct delete_dataset method
            # This would need to be implemented via REST API or LangSmith UI
            logger.info(f"Dataset {dataset_id} should be deleted manually from LangSmith UI")
        except Exception as e:
            logger.error(f"Failed to delete dataset from LangSmith: {e}")
            raise

    def sync_dataset_metadata(
        self,
        dataset_id: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Sync dataset metadata to LangSmith."""
        if not self.client:
            raise RuntimeError("LangSmith client not available")

        try:
            # Note: LangSmith Python client doesn't have a direct update_dataset method
            # This would need to be implemented via REST API
            logger.info(f"Dataset metadata sync not implemented yet for {dataset_id}")
        except Exception as e:
            logger.error(f"Failed to sync dataset metadata to LangSmith: {e}")
            raise

    def get_dataset_info(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get dataset information from LangSmith."""
        if not self.client:
            return None

        try:
            # Note: LangSmith Python client doesn't have a direct get_dataset method
            # This would need to be implemented via REST API
            logger.info(f"Dataset info retrieval not implemented yet for {dataset_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get dataset info from LangSmith: {e}")
            return None

    def list_datasets(self, project_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List datasets from LangSmith."""
        if not self.client:
            return []

        try:
            datasets = list(self.client.list_datasets())
            return [
                {
                    "id": dataset.id,
                    "name": dataset.name,
                    "description": dataset.description,
                    "data_type": dataset.data_type,
                }
                for dataset in datasets
            ]
        except Exception as e:
            logger.error(f"Failed to list datasets from LangSmith: {e}")
            return []

    def import_dataset(
        self,
        langsmith_dataset_id: str,
        local_name: str,
    ) -> Dict[str, Any]:
        """Import dataset from LangSmith."""
        if not self.client:
            raise RuntimeError("LangSmith client not available")

        try:
            # Get dataset examples
            examples = list(self.client.list_examples(dataset_id=langsmith_dataset_id))
            
            # Get dataset info
            dataset_info = self.get_dataset_info(langsmith_dataset_id)
            
            return {
                "dataset_info": dataset_info,
                "examples": examples,
                "local_name": local_name,
            }
        except Exception as e:
            logger.error(f"Failed to import dataset from LangSmith: {e}")
            raise 