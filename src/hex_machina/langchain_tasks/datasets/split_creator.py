"""Dataset split creation using evaluators."""

import logging

from langsmith import Client

from ..evaluation.registry import evaluator_registry


def create_split_with_evaluator(
    dataset_name: str, evaluator_name: str, split_name: str = "positive"
) -> None:
    """Create a split with positive examples from an evaluator.

    Args:
        dataset_name: Name of the LangSmith dataset to evaluate
        evaluator_name: Name of the evaluator to use
        split_name: Name for the new split (default: positive)
    """
    logger = logging.getLogger("langchain_tasks.datasets.split_creator")

    try:
        logger.info(f"Starting split creation for dataset: {dataset_name}")
        logger.info(f"Using evaluator: {evaluator_name}")
        logger.info(f"Split name: {split_name}")

        # Get the evaluator from the registry
        logger.info("Retrieving evaluator from registry...")
        evaluator = evaluator_registry.get_evaluator(evaluator_name)
        logger.info(f"Successfully retrieved evaluator: {type(evaluator).__name__}")

        # Get the LangSmith client and load the dataset
        logger.info(f"Loading dataset: {dataset_name}")
        client = Client()

        # List available datasets to find the exact name
        datasets = list(client.list_datasets())
        logger.info(f"Found {len(datasets)} available datasets")

        # Find the dataset by name (partial match)
        target_dataset = None
        for dataset in datasets:
            if dataset_name in dataset.name:
                target_dataset = dataset
                logger.info(
                    f"Found matching dataset: {dataset.name} (ID: {dataset.id})"
                )
                break

        if not target_dataset:
            logger.error(f"Dataset '{dataset_name}' not found")
            logger.info("Available datasets:")
            for dataset in datasets[:10]:  # Show first 10
                logger.info(f"  - {dataset.name}")
            if len(datasets) > 10:
                logger.info(f"  ... and {len(datasets) - 10} more")
            raise ValueError(f"Dataset '{dataset_name}' not found")

        # Get examples from the dataset
        examples = list(client.list_examples(dataset_id=target_dataset.id))
        logger.info(f"Loaded {len(examples)} examples from dataset")

        # Apply the evaluator to all examples
        logger.info("Applying evaluator to examples...")
        results = []
        for example in examples:
            try:
                # For function-based evaluators, we need run and example
                # Since we don't have run data, we'll pass empty dicts
                result = evaluator(run={}, example=example)
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to evaluate example: {e}")
                results.append(False)  # Default to False on error

        logger.info(f"Evaluation completed for {len(results)} examples")

        # Filter positive examples (where evaluator returned True)
        positive_examples = []
        for i, (example, result) in enumerate(zip(examples, results)):
            if result:
                positive_examples.append(example)
                logger.debug(f"Example {i} passed evaluation")
            else:
                logger.debug(f"Example {i} failed evaluation")

        logger.info(
            f"Found {len(positive_examples)} positive examples out of {len(examples)} total"
        )

        # Create the split using LangSmith client
        if positive_examples:
            logger.info(
                f"Creating split '{evaluator_name}' with {len(positive_examples)} examples..."
            )

            # Create the split using update_dataset_splits
            try:
                # Get the example IDs for the positive examples
                positive_example_ids = [example.id for example in positive_examples]

                # Update the dataset with the new split
                client.update_dataset_splits(
                    dataset_id=target_dataset.id,
                    split_name=evaluator_name,
                    example_ids=positive_example_ids,
                )

                logger.info(
                    f"Split '{evaluator_name}' created successfully with {len(positive_examples)} examples"
                )
                logger.info("Split creation completed successfully!")
                logger.info(f"Dataset: {target_dataset.name}")
                logger.info(f"Split: {evaluator_name}")
                logger.info(f"Examples in split: {len(positive_examples)}")

            except Exception as e:
                logger.error(f"Failed to create split using update_dataset_splits: {e}")
                raise
        else:
            logger.warning("No positive examples found - no split created")

    except Exception as e:
        logger.error(f"Failed to create split: {e}")
        raise


def delete_split(dataset_name: str, split_name: str) -> None:
    """Delete a split from a dataset.

    Args:
        dataset_name: Name of the LangSmith dataset
        split_name: Name of the split to delete
    """
    logger = logging.getLogger("langchain_tasks.datasets.split_creator")

    try:
        logger.info(f"Starting split deletion for dataset: {dataset_name}")
        logger.info(f"Split to delete: {split_name}")

        # Get the LangSmith client
        client = Client()

        # List available datasets to find the exact name
        datasets = list(client.list_datasets())
        logger.info(f"Found {len(datasets)} available datasets")

        # Find the dataset by name (partial match)
        target_dataset = None
        for dataset in datasets:
            if dataset_name in dataset.name:
                target_dataset = dataset
                logger.info(
                    f"Found matching dataset: {dataset.name} (ID: {dataset.id})"
                )
                break

        if not target_dataset:
            logger.error(f"Dataset '{dataset_name}' not found")
            logger.info("Available datasets:")
            for dataset in datasets[:10]:  # Show first 10
                logger.info(f"  - {dataset.name}")
            if len(datasets) > 10:
                logger.info(f"  ... and {len(datasets) - 10} more")
            raise ValueError(f"Dataset '{dataset_name}' not found")

        # Check if the split exists by looking at the dataset splits
        dataset_splits = client.list_dataset_splits(dataset_id=target_dataset.id)
        logger.info(f"Dataset splits: {dataset_splits}")

        if not dataset_splits:
            logger.warning(f"Dataset '{dataset_name}' has no splits")
            return

        # Check if the split exists
        if split_name not in dataset_splits:
            logger.warning(
                f"Split '{split_name}' not found in dataset '{dataset_name}'"
            )
            logger.info("Available splits:")
            for split in dataset_splits:
                logger.info(f"  - {split}")
            return

        logger.info(f"Found split '{split_name}' in dataset '{dataset_name}'")

        # Delete the split by removing all examples from it
        logger.info(
            f"Removing all examples from split '{split_name}' in dataset '{dataset_name}'..."
        )

        # First, we need to get the examples currently in the split
        # We can get this from the dataset examples that have this split
        try:
            # Get examples from the specific split
            split_examples = list(
                client.list_examples(
                    dataset_name=target_dataset.name, splits=[split_name]
                )
            )
            logger.info(f"Found {len(split_examples)} examples in split '{split_name}'")

            if split_examples:
                # Get the example IDs to remove
                example_ids_to_remove = [example.id for example in split_examples]

                # Remove all examples from the split
                client.update_dataset_splits(
                    dataset_id=target_dataset.id,
                    split_name=split_name,
                    example_ids=example_ids_to_remove,
                    remove=True,  # Remove these examples from the split
                )

                logger.info(
                    f"Split '{split_name}' cleared successfully from dataset '{dataset_name}'"
                )
            else:
                logger.info(f"Split '{split_name}' is already empty")

        except Exception as e:
            logger.error(f"Failed to clear split: {e}")
            raise

    except Exception as e:
        logger.error(f"Failed to delete split: {e}")
        raise
