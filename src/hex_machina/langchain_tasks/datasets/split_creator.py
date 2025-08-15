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
