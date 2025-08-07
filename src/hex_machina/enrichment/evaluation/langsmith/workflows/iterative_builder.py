"""Iterative dataset building workflow using LangSmith feedback."""

import logging
from typing import Any, Dict, List, Optional

from langsmith import Client

from ...models.evaluation_models import ContentCompletenessEvaluation
from ..datasets.dataset_manager import EvaluationDatasetManager
from ..utils.dataset_naming import DatasetNamingConvention


class IterativeDatasetBuilder:
    """Build iterative datasets using manual feedback from LangSmith."""

    def __init__(
        self,
        client: Optional[Client] = None,
        dataset_manager: Optional[EvaluationDatasetManager] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the iterative dataset builder.

        Args:
            client: LangSmith client. If None, creates a new one.
            dataset_manager: Dataset manager. If None, creates a new one.
            logger: Optional logger instance.
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.client = client or Client()
        self.dataset_manager = dataset_manager or EvaluationDatasetManager(
            client=client, logger=logger
        )

    async def build_iterative_dataset(
        self,
        source_dataset_name: str,
        content_category: str,
        prompt_version: str = "v1_0",
        iteration: Optional[int] = None,
        feedback_threshold: float = 0.8,
    ) -> str:
        """Build an iterative dataset from manual feedback.

        Args:
            source_dataset_name: Name of the source dataset.
            content_category: Category of content.
            prompt_version: Version of the prompt being tested.
            iteration: Iteration number. If None, auto-increments.
            feedback_threshold: Minimum confidence threshold for inclusion.

        Returns:
            Name of the created iterative dataset.
        """
        self.logger.info(f"Building iterative dataset from {source_dataset_name}")

        # Get source dataset
        source_dataset = self.dataset_manager.get_dataset(source_dataset_name)
        if not source_dataset:
            raise ValueError(f"Source dataset not found: {source_dataset_name}")

        # Get manual feedback from LangSmith
        feedback_data = await self._collect_manual_feedback(source_dataset)

        # Generate iterative dataset name
        if iteration is None:
            iteration = DatasetNamingConvention.get_next_iteration_number(
                source_dataset_name
            )

        iterative_dataset_name = DatasetNamingConvention.create_iterative_dataset_name(
            content_category=content_category,
            version=prompt_version,
            iteration=iteration,
        )

        # Create improved ground truth based on feedback
        improved_ground_truth = self._create_improved_ground_truth(
            feedback_data, feedback_threshold
        )

        # Create the iterative dataset
        examples = list(self.client.list_examples(dataset_id=source_dataset.id))
        articles = [
            self.dataset_manager._create_mock_article_from_example(example)
            for example in examples
        ]

        iterative_dataset = self.dataset_manager.create_test_dataset_from_articles(
            articles=articles,
            dataset_name=iterative_dataset_name,
            ground_truth_data=improved_ground_truth,
        )

        self.logger.info(
            f"Created iterative dataset: {iterative_dataset_name} "
            f"with {len(improved_ground_truth)} improved ground truth entries"
        )

        return iterative_dataset_name

    async def _collect_manual_feedback(self, dataset) -> Dict[str, Dict[str, Any]]:
        """Collect manual feedback from LangSmith dataset.

        Args:
            dataset: LangSmith dataset.

        Returns:
            Dictionary mapping example IDs to feedback data.
        """
        feedback_data = {}

        # Get all examples from the dataset
        examples = list(self.client.list_examples(dataset_id=dataset.id))

        for example in examples:
            example_id = str(example.id)
            url = example.inputs.get("url", "unknown")

            # Check for manual feedback in metadata
            metadata = example.metadata or {}
            human_labeled = metadata.get("human_labeled", "false")
            requires_manual_review = metadata.get("requires_manual_review", False)

            if human_labeled == "true" or requires_manual_review:
                # This example has been manually reviewed
                feedback_data[example_id] = {
                    "url": url,
                    "example_id": example_id,
                    "original_outputs": example.outputs or {},
                    "metadata": metadata,
                    "has_manual_feedback": True,
                    "confidence": metadata.get("confidence", "low"),
                    "requires_manual_review": requires_manual_review,
                }
            else:
                # No manual feedback yet
                feedback_data[example_id] = {
                    "url": url,
                    "example_id": example_id,
                    "original_outputs": example.outputs or {},
                    "metadata": metadata,
                    "has_manual_feedback": False,
                    "confidence": metadata.get("confidence", "low"),
                    "requires_manual_review": requires_manual_review,
                }

        self.logger.info(
            f"Collected feedback for {len(feedback_data)} examples "
            f"({sum(1 for f in feedback_data.values() if f['has_manual_feedback'])} with manual feedback)"
        )

        return feedback_data

    def _create_improved_ground_truth(
        self, feedback_data: Dict[str, Dict[str, Any]], confidence_threshold: float
    ) -> Dict[str, Dict[str, Any]]:
        """Create improved ground truth based on manual feedback.

        Args:
            feedback_data: Feedback data from manual review.
            confidence_threshold: Minimum confidence for inclusion.

        Returns:
            Improved ground truth data.
        """
        improved_ground_truth = {}

        for example_id, feedback in feedback_data.items():
            url = feedback["url"]
            original_outputs = feedback["original_outputs"]
            metadata = feedback["metadata"]

            if feedback["has_manual_feedback"]:
                # Use manual feedback when available
                improved_ground_truth[url] = {
                    "is_complete": original_outputs.get("is_complete", False),
                    "detected_issues": original_outputs.get("detected_issues", []),
                    "notes": f"Manual review: {metadata.get('notes', 'No notes')}",
                    "requires_manual_review": False,  # Already reviewed
                    "confidence": "high",  # Manual review is high confidence
                    "evaluation_method": "manual_review",
                    "evaluation_prompt": "manual_feedback",
                    "evaluation_model": "human_expert",
                    "feedback_source": "langsmith_manual_review",
                    "iteration_improved": True,
                }
            elif metadata.get("confidence") == "high":
                # Use high-confidence automated evaluation
                improved_ground_truth[url] = {
                    "is_complete": original_outputs.get("is_complete", False),
                    "detected_issues": original_outputs.get("detected_issues", []),
                    "notes": f"High-confidence automated evaluation: {metadata.get('notes', 'No notes')}",
                    "requires_manual_review": False,
                    "confidence": "high",
                    "evaluation_method": metadata.get("evaluation_method", "automated"),
                    "evaluation_prompt": metadata.get("evaluation_prompt", "unknown"),
                    "evaluation_model": metadata.get("evaluation_model", "unknown"),
                    "feedback_source": "high_confidence_automated",
                    "iteration_improved": True,
                }
            else:
                # Keep as-is for manual review
                improved_ground_truth[url] = {
                    "is_complete": original_outputs.get("is_complete", False),
                    "detected_issues": original_outputs.get("detected_issues", []),
                    "notes": f"Requires manual review: {metadata.get('notes', 'Low confidence automated evaluation')}",
                    "requires_manual_review": True,
                    "confidence": "low",
                    "evaluation_method": metadata.get("evaluation_method", "automated"),
                    "evaluation_prompt": metadata.get("evaluation_prompt", "unknown"),
                    "evaluation_model": metadata.get("evaluation_model", "unknown"),
                    "feedback_source": "requires_manual_review",
                    "iteration_improved": False,
                }

        # Calculate statistics
        manual_reviewed = sum(
            1
            for gt in improved_ground_truth.values()
            if gt["feedback_source"] == "langsmith_manual_review"
        )
        high_confidence = sum(
            1
            for gt in improved_ground_truth.values()
            if gt["feedback_source"] == "high_confidence_automated"
        )
        needs_review = sum(
            1 for gt in improved_ground_truth.values() if gt["requires_manual_review"]
        )

        self.logger.info(
            f"Improved ground truth: {manual_reviewed} manual reviews, "
            f"{high_confidence} high-confidence automated, {needs_review} need review"
        )

        return improved_ground_truth

    async def create_curated_dataset(
        self,
        iterative_dataset_name: str,
        content_category: str,
        curation_type: str = "validated",
        min_confidence: str = "high",
    ) -> str:
        """Create a curated dataset from iterative dataset.

        Args:
            iterative_dataset_name: Name of the iterative dataset.
            content_category: Category of content.
            curation_type: Type of curation.
            min_confidence: Minimum confidence level for inclusion.

        Returns:
            Name of the created curated dataset.
        """
        self.logger.info(f"Creating curated dataset from {iterative_dataset_name}")

        # Get iterative dataset
        iterative_dataset = self.dataset_manager.get_dataset(iterative_dataset_name)
        if not iterative_dataset:
            raise ValueError(f"Iterative dataset not found: {iterative_dataset_name}")

        # Get examples and filter by confidence
        examples = list(self.client.list_examples(dataset_id=iterative_dataset.id))
        curated_examples = []

        for example in examples:
            metadata = example.metadata or {}
            confidence = metadata.get("confidence", "low")

            # Include based on confidence level
            if self._meets_confidence_threshold(confidence, min_confidence):
                curated_examples.append(example)

        # Create curated dataset name
        curated_dataset_name = DatasetNamingConvention.create_curated_dataset_name(
            content_category=content_category,
            curation_type=curation_type,
        )

        # Create curated dataset with only high-confidence examples
        articles = [
            self.dataset_manager._create_mock_article_from_example(example)
            for example in curated_examples
        ]

        curated_dataset = self.dataset_manager.create_test_dataset_from_articles(
            articles=articles,
            dataset_name=curated_dataset_name,
            ground_truth_data={
                example.inputs.get("url"): example.outputs
                for example in curated_examples
                if example.outputs
            },
        )

        self.logger.info(
            f"Created curated dataset: {curated_dataset_name} "
            f"with {len(curated_examples)} high-confidence examples"
        )

        return curated_dataset_name

    def _meets_confidence_threshold(self, confidence: str, min_confidence: str) -> bool:
        """Check if confidence meets minimum threshold.

        Args:
            confidence: Current confidence level.
            min_confidence: Minimum required confidence.

        Returns:
            True if confidence meets threshold.
        """
        confidence_levels = {"low": 1, "medium": 2, "high": 3}

        current_level = confidence_levels.get(confidence.lower(), 1)
        min_level = confidence_levels.get(min_confidence.lower(), 1)

        return current_level >= min_level

    async def evaluate_model_on_dataset(
        self,
        dataset_name: str,
        model_name: str,
        prompt_version: str,
        evaluator,
    ) -> List[ContentCompletenessEvaluation]:
        """Evaluate a model on a dataset and track results.

        Args:
            dataset_name: Name of the dataset to evaluate.
            model_name: Name of the model being evaluated.
            prompt_version: Version of the prompt being tested.
            evaluator: The evaluator to use.

        Returns:
            List of evaluation results.
        """
        self.logger.info(f"Evaluating {model_name} on {dataset_name}")

        # Get dataset
        dataset = self.dataset_manager.get_dataset(dataset_name)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_name}")

        # Run evaluation
        results = await self.dataset_manager.run_evaluation_on_dataset(
            dataset=dataset,
            evaluator=evaluator,
            run_name=f"eval_{model_name}_{prompt_version}",
        )

        # Calculate metrics
        total = len(results)
        complete = sum(1 for r in results if r.is_complete)
        accuracy = complete / total if total > 0 else 0

        self.logger.info(
            f"Evaluation complete: {complete}/{total} complete ({accuracy:.1%} accuracy)"
        )

        return results

    async def compare_models_on_dataset(
        self,
        dataset_name: str,
        models: List[str],
        prompt_version: str,
        evaluator_factory,
    ) -> Dict[str, Dict[str, Any]]:
        """Compare multiple models on the same dataset.

        Args:
            dataset_name: Name of the dataset to evaluate.
            models: List of model names to compare.
            prompt_version: Version of the prompt being tested.
            evaluator_factory: Function to create evaluator for each model.

        Returns:
            Dictionary of results for each model.
        """
        self.logger.info(f"Comparing {len(models)} models on {dataset_name}")

        results = {}

        for model_name in models:
            try:
                # Create evaluator for this model
                evaluator = evaluator_factory(model_name)

                # Evaluate
                model_results = await self.evaluate_model_on_dataset(
                    dataset_name=dataset_name,
                    model_name=model_name,
                    prompt_version=prompt_version,
                    evaluator=evaluator,
                )

                # Calculate metrics
                total = len(model_results)
                complete = sum(1 for r in model_results if r.is_complete)
                accuracy = complete / total if total > 0 else 0
                avg_time = (
                    sum(r.processing_time_seconds for r in model_results) / total
                    if total > 0
                    else 0
                )

                results[model_name] = {
                    "total": total,
                    "complete": complete,
                    "incomplete": total - complete,
                    "accuracy": accuracy,
                    "avg_time": avg_time,
                    "results": model_results,
                }

            except Exception as e:
                self.logger.error(f"Failed to evaluate {model_name}: {e}")
                results[model_name] = {"error": str(e)}

        return results
